#!/usr/bin/env python3
"""List git worktrees with cleanup verdicts and remove verified ones; branches are never deleted."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402

CLI = "wt-sweep"
COMMANDS = ["list", "remove", "usage"]
SCHEMA = "wt-sweep.list.v1"
DEFAULT_ROOT = "~/Documents/projects"
DEFAULT_REGISTRY = ["~/.ai/contexts/*.md", "~/Documents/me/Projects/*/index.md"]
# Path components that mark operations / CLI execution records; these always need the user.
OPERATION_PARTS = {"runs", "outputs", "operations"}
# Installed dependency trees ship their own dirs with those names (npm es-abstract has operations/).
DEPENDENCY_PARTS = {"node_modules"}
INJECTED_FILE = "AGENTS.md"
INJECTED_BLOCK_RE = re.compile(
    r"<!-- coding-conventions:begin (\S+) -->.*?<!-- coding-conventions:end \1 -->\n?", re.S)
REF_END_RE = re.compile(r"[\s`'\"，；。、）)\]>]")
# Reflog subjects that mean the branch carried its own work; creation, resets and fast-forwards do not.
OWN_WORK = ("commit", "cherry-pick", "revert")
VERDICT_ORDER = ["removable", "ask", "keep", "prunable"]
VERDICT_TITLE = {
    "removable": "可删除",
    "ask": "需要你确认",
    "keep": "保留",
    "prunable": "失效记录（目录已不存在）",
}


class SweepError(Exception):
    """Stable CLI error carrying a category for the caller."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


def git(cwd: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git in cwd; failures surface the failed git operation."""

    proc = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SweepError("git", f"git {' '.join(args[:2])} failed in {cwd}: {proc.stderr.strip()}")
    return proc


def check_roots(roots: list[str]) -> None:
    """A scan root at or above home would put every repository's worktrees in reach."""

    home = os.path.realpath(Path.home())
    for root in roots:
        real = os.path.realpath(root)
        if os.path.commonpath([real, home]) == real:
            raise SweepError("path", f"scan root is too broad: {root}")


def inside(base: str, name: str) -> Path:
    """The path of a status entry; anything that resolves to base itself or outside it is refused."""

    real = os.path.realpath(base)
    target = os.path.normpath(os.path.join(real, name))
    parent = os.path.realpath(os.path.dirname(target))
    if os.path.isabs(name) or target == real or os.path.commonpath([real, parent]) != real:
        raise SweepError("path", f"refusing to delete outside the worktree: {name!r}")
    return Path(target)


def discover(roots: list[str], repos: list[str]) -> tuple[list[dict[str, Any]], int]:
    """Find worktrees of every repo checked out under roots; returns entries and skipped count."""

    mains: set[str] = set()
    for root in roots:
        if not Path(root).is_dir():
            raise SweepError("os", f"scan root does not exist: {root}")
        for child in sorted(Path(root).iterdir()):
            if not (child / ".git").exists():
                continue
            common = git(str(child), "rev-parse", "--path-format=absolute", "--git-common-dir",
                         check=False).stdout.strip()
            if common.endswith("/.git"):
                mains.add(common[: -len("/.git")])
    entries, skipped = [], 0
    for main in sorted(mains):
        if repos and Path(main).name not in repos:
            continue
        porcelain = git(main, "worktree", "list", "--porcelain").stdout
        for block in porcelain.strip().split("\n\n"):
            fields: dict[str, str] = {}
            for line in block.splitlines():
                key, _, value = line.partition(" ")
                fields[key] = value
            path = fields.get("worktree", "")
            if not path or path == main:
                continue
            prunable = "prunable" in fields
            if not prunable and not any(path.startswith(root.rstrip("/") + "/") for root in roots):
                skipped += 1
                continue
            entries.append({
                "path": path,
                "main": main,
                "branch": fields.get("branch", "").removeprefix("refs/heads/") or None,
                "head": fields.get("HEAD"),
                "prunable": prunable,
            })
    return entries, skipped


def load_registry(patterns: list[str]) -> list[tuple[str, int, str]]:
    """Read registry lines (contexts, project indexes) once for path lookups."""

    lines = []
    for pattern in patterns:
        for name in sorted(glob.glob(os.path.expanduser(pattern))):
            try:
                text = Path(name).read_text(encoding="utf-8")
            except OSError:
                continue
            lines.extend((name, number, line) for number, line in enumerate(text.splitlines(), 1))
    return lines


def registry_refs(path: str, registry: list[tuple[str, int, str]]) -> tuple[list[str], set[str]]:
    """Return file:line registrations of path and the sub-paths those lines reference."""

    home = str(Path.home())
    places, subpaths = [], set()
    pattern = re.compile(re.escape(path) + r"(?=$|[/\s`'\"，；。、）)\]>:])")
    for name, number, line in registry:
        hits = list(pattern.finditer(line))
        if not hits:
            continue
        places.append(f"{name.replace(home, '~')}:{number}")
        for hit in hits:
            rest = line[hit.end():]
            if rest.startswith("/"):
                sub = REF_END_RE.split(rest[1:], maxsplit=1)[0].rstrip("/.:")
                if sub:
                    subpaths.add(sub)
    return places, subpaths


def query_mr(path: str, branch: str) -> dict[str, Any] | None:
    """Return the newest MR whose source branch is branch, or None."""

    proc = subprocess.run(["glab", "mr", "list", "--source-branch", branch, "--all", "--output", "json"],
                          cwd=path, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()[:1]
        text = " ".join(detail)
        if re.search(r"no such host|dial tcp|timeout|network|connection refused", text, re.I):
            raise SweepError("network", text)
        if re.search(r"401|403|unauthori[sz]ed|forbidden|auth", text, re.I):
            raise SweepError("auth", text)
        raise SweepError("glab", text)
    mrs = json.loads(proc.stdout or "[]")
    if not mrs:
        return None
    mr = max(mrs, key=lambda item: item.get("created_at") or "")
    return {
        "iid": mr["iid"],
        "state": mr["state"],
        "sha": mr.get("sha") or "",
        "target": mr.get("target_branch"),
        "merged_at": (mr.get("merged_at") or "")[:10] or None,
        "closed_at": (mr.get("closed_at") or "")[:10] or None,
        "url": mr.get("web_url"),
    }


def local_merge(entry: dict[str, Any]) -> tuple[str | None, str]:
    """Without an MR, a branch is delivered when it had its own commits and HEAD is in the default branch.

    Returns the default branch, or None and the reason to keep. A fresh or pinned branch also sits inside the
    default branch, so ancestry alone cannot tell it from a merged one."""

    main, branch = entry["main"], entry["branch"]
    ref = git(main, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False).stdout.strip()
    if not ref.startswith("origin/"):
        return None, "没有 MR，也没有 origin/HEAD，无法判断 default branch"
    target = ref.removeprefix("origin/")
    if branch == target:
        return None, f"worktree 在 default branch {target} 上"
    subjects = git(main, "reflog", "show", "--format=%gs", f"refs/heads/{branch}", check=False).stdout.splitlines()
    if not any(subject.startswith(OWN_WORK) for subject in subjects):
        return None, "没有 MR，分支 reflog 里没有自己的提交（新建、固定用途或 reflog 已过期）"
    for candidate in (f"refs/heads/{target}", f"refs/remotes/origin/{target}"):
        if git(main, "merge-base", "--is-ancestor", entry["head"], candidate, check=False).returncode == 0:
            return target, ""
    return None, f"没有 MR，HEAD 不在 {target} 上"


def injected_only(path: str) -> bool:
    """True when AGENTS.md differs from HEAD only inside coding-conventions blocks."""

    committed = git(path, "show", f"HEAD:{INJECTED_FILE}", check=False)
    if committed.returncode != 0:
        return False
    current = (Path(path) / INJECTED_FILE).read_text(encoding="utf-8")
    strip = lambda text: re.sub(r"\n{2,}", "\n", INJECTED_BLOCK_RE.sub("", text)).strip()  # noqa: E731
    return strip(committed.stdout) == strip(current)


def status_entries(path: str) -> tuple[list[str], list[str], list[str]]:
    """Return tracked changes, untracked entries and ignored entries relative to the worktree.

    -z keeps names raw; without it git quotes non-ASCII names and the paths would not match the files."""

    fields = iter(git(path, "status", "--porcelain", "-z", "--ignored").stdout.split("\0"))
    tracked, untracked, ignored = [], [], []
    for field in fields:
        if not field:
            continue
        code, name = field[:2], field[3:]
        if "R" in code or "C" in code:
            next(fields, None)  # the source path of a rename or copy
        (untracked if code == "??" else ignored if code == "!!" else tracked).append(name)
    return tracked, untracked, ignored


def operation_record(worktree: Path, name: str, depth: int = 3) -> str | None:
    """Find an operations-record directory at or inside a collapsed status entry."""

    if DEPENDENCY_PARTS & set(Path(name).parts):
        return None
    if OPERATION_PARTS & set(Path(name).parts):
        return name
    top = worktree / name.rstrip("/")
    if top.is_symlink() or not top.is_dir():
        return None
    for current, dirs, _ in os.walk(top):
        rel = Path(current).relative_to(worktree)
        hits = sorted(OPERATION_PARTS & set(dirs))
        if hits:
            return f"{rel / hits[0]}/"
        if len(rel.parts) >= depth:
            dirs.clear()
        dirs[:] = [d for d in dirs if d not in DEPENDENCY_PARTS and not (Path(current) / d).is_symlink()]
    return None


def inspect(entry: dict[str, Any], registry: list[tuple[str, int, str]]) -> dict[str, Any]:
    """Collect facts for one worktree and decide removable / ask / keep / prunable."""

    path = entry["path"]
    item = dict(entry, mr=None, merged_into=None, reasons=[], also_deleted=[], prepare=[])
    item["registrations"], subpaths = registry_refs(path, registry)
    if entry["prunable"] or not Path(path).is_dir():
        item["verdict"] = "prunable"
        item["reasons"].append(f"目录不存在，执行 git -C {entry['main']} worktree prune 清除记录")
        return item
    keep = item["reasons"].append
    if not entry["branch"]:
        keep("detached HEAD，无法绑定 MR")
    else:
        try:
            item["mr"] = query_mr(path, entry["branch"])
        except (SweepError, subprocess.TimeoutExpired, ValueError) as exc:
            category = getattr(exc, "category", "glab")
            keep(f"MR 查询失败（{category}）：{exc}")
    mr = item["mr"]
    if entry["branch"] and not item["reasons"]:
        if mr is None:
            item["merged_into"], reason = local_merge(entry)
            if reason:
                keep(reason)
        elif mr["state"] not in ("merged", "closed"):
            keep(f"MR !{mr['iid']} {mr['state']}")
        elif entry["head"] != mr["sha"]:
            rel = git(path, "merge-base", "--is-ancestor", "HEAD", mr["sha"], check=False).returncode
            if rel == 128:
                keep(f"本地缺少 MR !{mr['iid']} 的最终 head {mr['sha'][:8]}，需先 fetch")
            elif rel != 0:
                keep(f"本地 HEAD 有 MR !{mr['iid']} 最终 head 之外的提交")
    tracked, untracked, ignored = status_entries(path)
    if tracked == [INJECTED_FILE] and injected_only(path):
        item["prepare"].append(f"还原 {INJECTED_FILE}（只有 coding-conventions 注入块）")
    elif tracked:
        keep(f"有未提交改动：{', '.join(tracked)}")
    for name in untracked:
        kind = "软链，只删链接" if (Path(path) / name.rstrip("/")).is_symlink() else "未跟踪"
        item["also_deleted"].append(f"{name}（{kind}）")
    item["also_deleted"].extend(f"{name}（忽略）" for name in ignored)
    if item["reasons"]:
        item["verdict"] = "keep"
        return item
    asks = []
    if item["merged_into"] and untracked:
        asks.append(f"没有 MR，未跟踪文件可能是没提交的新工作：{', '.join(untracked)}")
    for name in untracked + ignored:
        found = operation_record(Path(path), name)
        if found:
            asks.append(f"含 operations / CLI 执行记录：{found}")
        entry_path = Path(path) / name.rstrip("/")
        if not entry_path.is_symlink() and (entry_path / ".git").exists():
            asks.append(f"含嵌套的 git 仓库：{name}")
    for sub in sorted(subpaths):
        target = Path(path) / sub
        if target.exists() and git(path, "ls-files", "--error-unmatch", sub, check=False).returncode != 0:
            asks.append(f"登记引用了未跟踪 / 忽略文件：{sub}")
    item["reasons"] = asks
    item["verdict"] = "ask" if asks else "removable"
    if mr and mr["state"] == "closed":
        item["reasons"].append(f"MR !{mr['iid']} 是 closed（未合并）")
    return item


def sweep(roots: list[str], repos: list[str], registry: list[str]) -> dict[str, Any]:
    entries, skipped = discover(roots, repos)
    lines = load_registry(registry)
    with ThreadPoolExecutor(8) as pool:
        items = list(pool.map(lambda entry: inspect(entry, lines), entries))
    items.sort(key=lambda item: (VERDICT_ORDER.index(item["verdict"]), item["path"]))
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "roots": roots,
        "skipped_outside_roots": skipped,
        "items": items,
    }


def render(result: dict[str, Any]) -> str:
    """Human view: every path is spelled out with the facts behind its verdict."""

    items = result["items"]
    out = [f"wt-sweep list · {result['generated_at']} · {len(items)} 个 worktree · "
           f"root {', '.join(result['roots'])}"]
    if result["skipped_outside_roots"]:
        out.append(f"（另有 {result['skipped_outside_roots']} 个 worktree 不在 root 下，未列出）")
    for verdict in VERDICT_ORDER:
        group = [item for item in items if item["verdict"] == verdict]
        if not group:
            continue
        out.append(f"\n## {VERDICT_TITLE[verdict]}（{verdict}，{len(group)}）")
        for item in group:
            mr = item["mr"]
            mr_text = (f"MR !{mr['iid']} {mr['state']} {mr['merged_at'] or mr['closed_at'] or ''}".strip()
                       if mr else f"无 MR，已在 {item['merged_into']}" if item["merged_into"] else "无 MR")
            out.append(f"- {item['path']}")
            deletable = verdict in ("removable", "ask")
            if verdict != "prunable":
                out.append(f"    branch {item['branch'] or '(detached)'} · {mr_text} · "
                           f"HEAD {(item['head'] or '')[:8]}" + ("（删除后分支保留）" if deletable else ""))
            for reason in item["reasons"]:
                out.append(f"    原因：{reason}")
            if deletable:
                out.extend(f"    删除前：{step}" for step in item["prepare"])
                if item["also_deleted"]:
                    out.append(f"    连带删除：{'；'.join(item['also_deleted'])}")
            if item["registrations"]:
                out.append(f"    登记：{' '.join(item['registrations'])}")
    # remove only re-checks worktrees under its roots, so a non-default scan must carry them over.
    default_roots = [os.path.abspath(os.path.expanduser(DEFAULT_ROOT))]
    root_args = "".join(f" --root {r}" for r in result["roots"]) if result["roots"] != default_roots else ""
    for verdict, title in (("removable", "删除命令"), ("ask", "确认后的删除命令")):
        paths = [item["path"] for item in items if item["verdict"] == verdict]
        if paths:
            out.append(f"\n{title}：\n  wt-sweep remove{root_args} \\\n" + " \\\n".join(f"    {p}" for p in paths))
    return "\n".join(out)


def remove(paths: list[str], roots: list[str], registry: list[str], dry_run: bool) -> int:
    """Re-inspect each exact path and remove it only when its verdict still allows it."""

    wanted = [os.path.abspath(os.path.expanduser(p)) for p in paths]
    entries, _ = discover(roots, [])
    by_path = {entry["path"]: entry for entry in entries}
    lines = load_registry(registry)
    failed = 0
    for path in wanted:
        entry = by_path.get(path)
        if entry is None:
            print(f"REFUSED {path}: 不在 root 下的 worktree 列表中")
            failed += 1
            continue
        item = inspect(entry, lines)
        if item["verdict"] == "keep":
            print(f"REFUSED {path}: {'；'.join(item['reasons'])}")
            failed += 1
            continue
        if dry_run:
            steps = item["prepare"] + [f"删除 {name}" for name in item["also_deleted"]]
            print(f"WOULD REMOVE {path}" + (f"：{'；'.join(steps)}" if steps else ""))
            continue
        try:
            if item["verdict"] == "prunable":
                git(entry["main"], "worktree", "prune")
                print(f"PRUNED {path}")
                continue
            # Every target is checked before anything is deleted.
            main = os.path.realpath(entry["main"])
            if os.path.commonpath([os.path.realpath(path), main]) == os.path.realpath(path):
                raise SweepError("path", f"main checkout {main} is inside the worktree")
            targets = [inside(path, name) for name in status_entries(path)[1]]
            if item["prepare"]:
                git(path, "checkout", "--", INJECTED_FILE)
            for target in targets:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            git(entry["main"], "worktree", "remove", path)
        except (SweepError, OSError) as exc:
            print(f"FAILED {path}: {exc}")
            failed += 1
            continue
        print(f"REMOVED {path}（branch {item['branch'] or '(detached)'} 保留）")
    return 1 if failed else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=CLI,
        description=("List worktrees with cleanup verdicts, or remove exact paths after re-checking "
                     "them. Branches are never deleted. `usage` prints local call statistics."))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "remove"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", action="append", help=f"scan root (default {DEFAULT_ROOT})")
        cmd.add_argument("--registry", action="append",
                         help="registry glob for registrations (default contexts + project indexes)")
    sub.choices["list"].add_argument("--repo", action="append", default=[],
                                     help="only repos whose main checkout has this directory name")
    sub.choices["list"].add_argument("--json", action="store_true")
    sub.choices["remove"].add_argument("paths", nargs="+")
    sub.choices["remove"].add_argument("--dry-run", action="store_true")
    sub.add_parser("usage")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    if args.command == "usage":
        print(json.dumps(cli_usage.summarize(CLI, COMMANDS), ensure_ascii=False, indent=2))
        cli_usage.record(CLI, "usage", started, 0)
        return 0
    roots = [os.path.abspath(os.path.expanduser(r)) for r in (args.root or [DEFAULT_ROOT])]
    registry = args.registry or DEFAULT_REGISTRY
    try:
        check_roots(roots)
        if args.command == "list":
            result = sweep(roots, args.repo, registry)
            print(json.dumps(result, ensure_ascii=False, indent=1) if args.json else render(result))
            code = 0
        else:
            code = remove(args.paths, roots, registry, args.dry_run)
    except (SweepError, OSError) as exc:
        category = getattr(exc, "category", "os")
        print(f"error[{category}]: {exc}", file=sys.stderr)
        code = 1
    cli_usage.record(CLI, args.command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
