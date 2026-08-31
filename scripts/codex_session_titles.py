#!/usr/bin/env python3
"""Refresh Codex session titles from real user intent.

Title format: [abbr][MMdd] summary
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


CODEX_HOME = Path.home() / ".codex"
REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = CODEX_HOME / "state_5.sqlite"
INDEX_PATH = CODEX_HOME / "session_index.jsonl"
BACKUP_DIR = CODEX_HOME / "tmp" / "session-title-backups"
BACKUP_RETENTION_DAYS = 7
LOCAL_TZ = timezone(timedelta(hours=8))

NOISE_PREFIXES = (
    "# AGENTS.md instructions",
    "<INSTRUCTIONS>",
    "<environment_context>",
    "<turn_aborted>",
    "<goal_context>",
    "<local-command",
    "The user interrupted",
    "[Request interrupted",
    "<command-message>",
    "<command-name>",
    "<command-name>/load-context<",
    "执行 /load-context",
    "/load-context",
    "/clear",
)

PROJECT_RULES = [
    ("amt", ("<maintenance-checkout>", "load-context amt", "个人 ai 工具", "AI 工具配置管理")),
    ("hw", ("iam-vehicle", "invitation", "hw-test", "account-service", "VehicleApiController")),
    ("partner", ("iam-li-partner-service", "load-context partner")),
    ("sma", ("service-meta-agent", "service meta agent")),
    ("gtd", ("Projects/gtd", "ticktick", "daily-report")),
    ("larkbot", ("larkbot", "lark-cli")),
    ("symphony-lite", ("symphony-lite",)),
    ("aisp", ("aisp",)),
    ("ai-workshop", ("AI_trans_workshop", "ai workshop", "睡眠训练")),
    ("arch-hub", ("arch-hub", "mermaid")),
    ("idaas", ("idaas", "/batch 接口")),
    ("tools", ("zread",)),
    ("codex", ("codex tui", "修复 TUI", "Operation not permitted", "终端")),
]

GENERIC_CWD_PARTS = {"Projects", "projects", "me", "Documents"}

SUMMARY_RULES = [
    (r"修复 TUI|Operation not permitted|终端.*chrome|session.*名字|历史.*session", "修复 TUI 启动权限错误"),
    (r"account-service.*时区|时区问题", "处理 account-service 时区问题"),
    (r"api lintest.*invitation|lintest.*invitation", "跑通 api lintest invitation"),
    (r"service lintest.*invitation", "service lintest invitation 历史会话"),
    (r"invitation remote error|remote error", "修复 invitation remote error 响应"),
    (r"larkbot.*本地|本地启动", "larkbot 本地启动"),
    (r"rebase.*origin/master", "rebase origin/master"),
    (r"test.*结构.*重构|重构.*test", "test 结构重构后续"),
    (r"整理收尾.*test|test.*文件", "收尾 test 文件结构"),
    (r"日报|daily report|Automation:", "生成日报"),
]


def clean_text(value: Any) -> str:
    if not value:
        return ""
    text = str(value)
    text = re.sub(r"<command-message>.*?</command-message>", " ", text, flags=re.S)
    text = re.sub(r"\[Request interrupted[^\]]*\]", " ", text, flags=re.I)
    text = re.sub(r"The user interrupted[^\n]*", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def is_noise(text: str) -> bool:
    text = clean_text(text)
    if not text or any(text.startswith(prefix) for prefix in NOISE_PREFIXES):
        return True
    if text.lower() in {"ok", "okay", "yes", "好的", "是的", "嗯"}:
        return True
    if text.startswith("<skill>"):
        return True
    if re.match(r"^/?\$?load-context(?:\s+\S+)?$", text):
        return True
    return bool(re.match(r"^\[\$[A-Za-z0-9_-]+\]\([^)]+\)(?:\s+\S+)?$", text))


def load_context_arg(text: str) -> str:
    text = clean_text(text)
    match = re.match(
        r"^\[\$load-context\]\([^)]+\)(?:\s+([A-Za-z0-9_-]+(?::[A-Za-z0-9_-]+)?))?(?:\s+.*)?$",
        text,
    )
    if not match:
        match = re.match(
            r"^(?:执行\s+)?/?\$?load-context(?:\s+([A-Za-z0-9_-]+(?::[A-Za-z0-9_-]+)?))?(?:\s+.*)?$",
            text,
        )
    if not match:
        return ""
    spec = match.group(1) or ""
    return spec.split(":", 1)[0]


def project_rule_match(text: str) -> str:
    lower = clean_text(text).lower()
    for abbr, needles in PROJECT_RULES:
        if any(needle.lower() in lower for needle in needles):
            return abbr
    return ""


def cwd_abbr(cwd: str) -> str:
    cwd = clean_text(cwd)
    if not cwd:
        return ""
    try:
        if Path(cwd).expanduser().resolve() == REPO_ROOT:
            return "amt"
    except (OSError, RuntimeError):
        pass
    matched = project_rule_match(cwd)
    if matched:
        return matched
    if is_projects_root(cwd):
        return ""
    base = Path(cwd).name.strip()
    if base and base not in GENERIC_CWD_PARTS:
        return re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-").lower() or "work"
    return ""


def is_projects_root(cwd: str) -> bool:
    try:
        projects_root = Path.home() / "Documents" / "projects"
        return Path(clean_text(cwd)).expanduser().resolve() == projects_root
    except (OSError, RuntimeError):
        return False


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def user_messages_from_rollout(path: str | None, limit: int = 3) -> list[str]:
    if not path or not Path(path).exists():
        return []
    messages: list[str] = []
    for obj in read_jsonl(Path(path)):
        payload = obj.get("payload") if isinstance(obj, dict) else {}
        text = ""
        if obj.get("type") == "event_msg" and payload.get("type") == "user_message":
            text = payload.get("message") or ""
        elif obj.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
            parts = []
            for item in payload.get("content") or []:
                if isinstance(item, dict):
                    parts.append(item.get("text") or "")
                elif isinstance(item, str):
                    parts.append(item)
            text = " ".join(parts)
        text = clean_text(text)
        if is_noise(text):
            continue
        if messages and messages[-1] == text:
            continue
        messages.append(text)
        if len(messages) >= limit:
            break
    return messages


def candidate_user_texts(row: dict[str, Any], messages: list[str]) -> list[str]:
    texts = [row.get("first_user_message") or "", row.get("preview") or "", *messages]
    return [clean_text(text) for text in texts if clean_text(text)]


def non_noise_user_texts(row: dict[str, Any], messages: list[str]) -> list[str]:
    return [text for text in candidate_user_texts(row, messages) if not is_noise(text)]


def mmdd(timestamp: Any) -> str:
    try:
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(LOCAL_TZ).strftime("%m%d")
        seconds = float(timestamp)
        if seconds > 10_000_000_000:
            seconds /= 1000
        return datetime.fromtimestamp(seconds, LOCAL_TZ).strftime("%m%d")
    except Exception:
        return datetime.now(LOCAL_TZ).strftime("%m%d")


def infer_abbr(row: dict[str, Any], messages: list[str]) -> str:
    for text in candidate_user_texts(row, messages):
        arg = load_context_arg(text)
        if arg:
            return arg
    cwd = row.get("cwd") or ""
    matched = cwd_abbr(cwd)
    if matched:
        return matched
    user_haystack = " ".join(non_noise_user_texts(row, messages))
    if re.search(r"修复 TUI|codex tui|Operation not permitted|终端.*chrome|session.*名字|历史.*session", user_haystack, flags=re.I):
        return "codex"
    matched = project_rule_match(user_haystack)
    if matched:
        return matched
    if is_projects_root(cwd):
        return "projects"
    return "work"


def summarize(row: dict[str, Any], messages: list[str], abbr: str) -> str:
    haystack = clean_text(" ".join([
        *non_noise_user_texts(row, messages),
        row.get("title") or row.get("thread_name") or "",
        row.get("cwd") or "",
    ]))
    for pattern, summary in SUMMARY_RULES:
        if re.search(pattern, haystack, flags=re.I):
            return summary
    for message in messages:
        text = clean_text(message)
        text = re.sub(r"^你可以先\s*/load-context\s+\S+\s*[，,。]?\s*", "", text).strip()
        text = re.sub(r"^(我想让你|我需要你|请你|帮我|麻烦你)", "", text).strip()
        text = re.split(r"(，|,)\s*(已完成|你可以\s*/load-context|先\s*/load-context)", text)[0].strip()
        text = re.split(r"[。！？!?\n]", text)[0].strip(" ，,：:")
        if text and not is_noise(text):
            return text[:42]
    old = re.sub(r"^\[[^\]]+\]\[[^\]]+\]\s*", "", clean_text(row.get("title") or row.get("thread_name") or ""))
    if old and not is_noise(old):
        return old[:42]
    return f"{abbr} 历史会话"


def rollout_messages(row: dict[str, Any]) -> list[str]:
    return user_messages_from_rollout(row.get("rollout_path") or row.get("session_path") or row.get("path") or row.get("file_path"))


def title_abbr(title: str) -> str:
    match = re.match(r"^\[([^\]]+)\]\[[0-9]{4}\]\s+\S+", clean_text(title))
    return match.group(1) if match else ""


def daily_note_summary(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"^- ", "", text)
    text = re.sub(r"^\[\d{2}:\d{2}-\d{2}:\d{2}\]\s+", "", text)
    text = re.sub(r"^\d{2}:\d{2}\s+", "", text)
    return text[:42]


def title_for(row: dict[str, Any],
              messages: list[str] | None = None,
              summary_override: str = "") -> str:
    messages = messages if messages is not None else rollout_messages(row)
    abbr = infer_abbr(row, messages)
    summary = (
        daily_note_summary(summary_override)
        if summary_override else summarize(row, messages, abbr)
    )
    return f"[{abbr}][{mmdd(row.get('created_at') or row.get('created'))}] {summary}"


def needs_refresh(title: str) -> bool:
    title = clean_text(title)
    if not re.match(r"^\[[^\]]+\]\[[0-9]{4}\]\s+\S+", title):
        return True
    if title.startswith("[codex]"):
        return True
    noisy_fragments = (
        "历史会话",
        "加载上下文",
        "[$load-context]",
        "<environment_context>",
        "<command-name>",
        "<command-message>",
        "Request interrupted",
        "The user interrupted",
        "Operation not permitted",
    )
    return any(fragment in title for fragment in noisy_fragments)


def backup_files() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in [DB_PATH, DB_PATH.with_name(DB_PATH.name + "-wal"), DB_PATH.with_name(DB_PATH.name + "-shm"), INDEX_PATH]:
        if path.exists():
            shutil.copy2(path, BACKUP_DIR / f"{path.name}.{stamp}.bak")
    prune_old_backups()
    return stamp


def prune_old_backups(now: datetime | None = None) -> int:
    if not BACKUP_DIR.exists():
        return 0
    now = now or datetime.now()
    cutoff = now.timestamp() - BACKUP_RETENTION_DAYS * 24 * 60 * 60
    pruned = 0
    for path in BACKUP_DIR.glob("*.bak"):
        if not path.is_file():
            continue
        if path.stat().st_mtime >= cutoff:
            continue
        path.unlink()
        pruned += 1
    return pruned


def index_title(row: dict[str, Any]) -> str:
    for key in ("thread_name", "title", "name"):
        if key in row:
            return row.get(key) or ""
    return ""


def index_update_count(index_rows: list[dict[str, Any]], update_map: dict[str, str]) -> int:
    updates = 0
    for row in index_rows:
        thread_id = row.get("thread_id") or row.get("id") or row.get("conversation_id")
        if thread_id not in update_map:
            continue
        changed = False
        for key in ("thread_name", "title", "name"):
            if key in row and row[key] != update_map[thread_id]:
                changed = True
        if not any(key in row for key in ("thread_name", "title", "name")):
            changed = True
        if changed:
            updates += 1
    return updates


def update_index_titles(index_rows: list[dict[str, Any]], update_map: dict[str, str]) -> int:
    index_updates = 0
    if not INDEX_PATH.exists() or not update_map:
        return index_updates

    out = []
    for row in index_rows:
        thread_id = row.get("thread_id") or row.get("id") or row.get("conversation_id")
        if thread_id in update_map:
            touched = False
            changed = False
            for key in ("thread_name", "title", "name"):
                if key in row:
                    touched = True
                    if row[key] != update_map[thread_id]:
                        row[key] = update_map[thread_id]
                        changed = True
            if not touched:
                row["thread_name"] = update_map[thread_id]
                changed = True
            if changed:
                index_updates += 1
        out.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")))

    tmp = INDEX_PATH.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    tmp.replace(INDEX_PATH)
    return index_updates


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--current", action="store_true", help="refresh the newest session only")
    group.add_argument("--recent", action="store_true", help="refresh recent sessions only")
    group.add_argument("--all", action="store_true", help="refresh every session")
    parser.add_argument("--limit", type=int, default=30, help="recent session count")
    parser.add_argument("--set-title", help="set a specific title instead of inferring one")
    parser.add_argument(
        "--daily-note-title",
        help="use the beginning of the Daily Note timeline entry as the title summary",
    )
    parser.add_argument("--thread-id", help="thread id to update; defaults to newest thread with --set-title")
    parser.add_argument("--force-reinfer", action="store_true", help="re-infer titles even when they look valid")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Codex state not found; skipped")
        return 0

    index_rows = read_jsonl(INDEX_PATH)
    index_by_id = {
        row.get("thread_id") or row.get("id") or row.get("conversation_id"): row
        for row in index_rows
        if row.get("thread_id") or row.get("id") or row.get("conversation_id")
    }

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    current_thread_id = os.environ.get("CODEX_THREAD_ID", "")
    if args.current and current_thread_id:
        rows = [
            dict(row)
            for row in con.execute("select * from threads where id=?", (current_thread_id,)).fetchall()
        ]
    else:
        sql = "select * from threads order by updated_at desc, id desc"
        if args.current:
            sql += " limit 1"
        elif args.recent or not args.all:
            sql += f" limit {max(args.limit, 1)}"
        rows = [dict(row) for row in con.execute(sql).fetchall()]

    if args.set_title:
        target = args.thread_id
        if not target and rows:
            target = rows[0].get("id") or rows[0].get("thread_id")
        if not target:
            print("No Codex thread found; skipped")
            return 0
        row = next((row for row in rows if (row.get("id") or row.get("thread_id")) == target), None)
        if row is None:
            row = con.execute("select * from threads where id=?", (target,)).fetchone()
            row = dict(row) if row else None
        if row is None:
            print(f"Codex thread not found: {target}")
            return 1
        updates = [(target, row.get("title") or "", args.set_title)]
        if args.dry_run:
            for thread_id, old, new in updates:
                print(f"{thread_id}: {old!r} -> {new!r}")
            print("dry-run updates: 1")
            return 0

        stamp = backup_files()
        con.execute("update threads set title=? where id=?", (args.set_title, target))
        con.commit()
        con.close()
        index_updates = update_index_titles(index_rows, {target: args.set_title})
        print(f"Codex session title set: db=1, index={index_updates}, backup={stamp}")
        print(f"- {target}: {updates[0][1] or '(empty)'} -> {args.set_title}")
        return 0

    updates: list[tuple[str, str, str]] = []
    desired_index_titles: dict[str, str] = {}
    for row in rows:
        thread_id = row.get("id") or row.get("thread_id")
        if not thread_id:
            continue
        index_row = index_by_id.get(thread_id, {})
        current_title = row.get("title") or ""
        merged = {**index_row, **row}
        messages = rollout_messages(merged)
        inferred_abbr = infer_abbr(merged, messages)
        should_refresh = (
            args.force_reinfer or bool(args.daily_note_title)
            or needs_refresh(current_title)
            or title_abbr(current_title) != inferred_abbr
        )
        if not should_refresh:
            if index_row and index_title(index_row) != current_title:
                desired_index_titles[thread_id] = current_title
            continue
        new_title = title_for(merged, messages, args.daily_note_title or "")
        desired_index_titles[thread_id] = new_title
        if current_title != new_title:
            updates.append((thread_id, current_title, new_title))

    if args.dry_run:
        for thread_id, old, new in updates:
            print(f"{thread_id}: {old!r} -> {new!r}")
        print(f"dry-run db updates: {len(updates)}, index updates: {index_update_count(index_rows, desired_index_titles)}")
        return 0

    index_only_updates = index_update_count(index_rows, desired_index_titles)
    if not updates and not index_only_updates:
        print("Codex session titles refreshed: db=0, index=0, backup=skipped")
        return 0

    stamp = backup_files()
    for thread_id, _, new_title in updates:
        con.execute("update threads set title=? where id=?", (new_title, thread_id))
    con.commit()
    con.close()

    index_updates = update_index_titles(index_rows, desired_index_titles)

    print(f"Codex session titles refreshed: db={len(updates)}, index={index_updates}, backup={stamp}")
    if updates:
        print("Updated titles:")
        for thread_id, old, new in updates:
            print(f"- {thread_id}: {old or '(empty)'} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
