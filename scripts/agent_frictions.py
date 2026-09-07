#!/usr/bin/env python3
"""Collect and manage objective agent-friction events.

The collector deliberately reads only structured Codex rollout metadata. It
never persists user/assistant messages, tool inputs, or tool output bodies.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable

SCHEMA_VERSION = "agent.friction.event.v0"
SETTLED = {"promoted", "resolved", "ignored"}
RESOLUTIONS = SETTLED | {"deferred"}
MIN_REPEATED_PATCHES = 4
MIN_REPEATED_TURNS = 3


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def canonical_event_id(source_kind: str, source_id: str, event_type: str,
                       evidence_refs: Iterable[str]) -> str:
    identity = {
        "source_kind": source_kind,
        "source_id": source_id,
        "event_type": event_type,
        "evidence_refs": sorted(evidence_refs),
    }
    encoded = json.dumps(identity,
                         ensure_ascii=False,
                         sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def default_root() -> Path:
    return Path.home() / ".ai" / "frictions"


def default_inbox() -> Path:
    return Path.home() / ".ai" / "agent-frictions.md"


def locate_rollout(codex_home: Path, rollout: str | None,
                   thread_id: str | None) -> Path:
    if rollout:
        path = Path(rollout).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"rollout not found: {path}")
        return path
    if not thread_id:
        raise ValueError("provide --rollout or --thread-id")

    matches: list[Path] = []
    for base in (codex_home / "sessions", codex_home / "archived_sessions"):
        if base.exists():
            matches.extend(path for path in base.rglob("*.jsonl")
                           if thread_id in path.name)
    if not matches:
        raise ValueError(f"rollout not found for thread id: {thread_id}")
    if len(matches) != 1:
        joined = "\n".join(str(path) for path in sorted(matches))
        raise ValueError(f"multiple rollouts found for {thread_id}:\n{joined}")
    return matches[0]


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w",
                            encoding="utf-8",
                            dir=path.parent,
                            delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_write_text(path: Path, content: str) -> None:
    mode = path.stat().st_mode & 0o777
    with NamedTemporaryFile("w",
                            encoding="utf-8",
                            dir=path.parent,
                            delete=False) as handle:
        handle.write(content)
        os.fchmod(handle.fileno(), mode)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def owner_from_spec(spec: str) -> dict[str, Any]:
    if spec == "unclaimed":
        return {"kind": "unclaimed", "id": None}
    if spec.startswith("context:"):
        owner_id = spec.removeprefix("context:").strip()
        if ":" not in owner_id or not all(owner_id.split(":", 1)):
            raise ValueError("context owner must be context:<abbr>:<route>")
        return {"kind": "context", "id": owner_id}
    if spec.startswith("ll-contract:"):
        owner_id = spec.removeprefix("ll-contract:").strip()
        if not owner_id:
            raise ValueError("ll-contract owner requires an exact path")
        return {"kind": "ll_contract", "id": str(Path(owner_id).expanduser())}
    raise ValueError(
        "owner must be unclaimed, context:<abbr>:<route>, or ll-contract:<path>"
    )


def owner_key(owner: dict[str, Any]) -> str:
    kind = owner.get("kind")
    owner_id = owner.get("id")
    if kind == "unclaimed":
        return "unclaimed"
    if kind == "context":
        return f"context:{owner_id}"
    if kind == "ll_contract":
        return f"ll-contract:{owner_id}"
    return "invalid"


def normalize_path(path: str, cwd: str | None) -> str:
    candidate = Path(path)
    if not cwd or not candidate.is_absolute():
        return path
    try:
        return str(candidate.relative_to(Path(cwd)))
    except ValueError:
        return path


def event_path(root: Path, event: dict[str, Any]) -> Path:
    observed = parse_time(str(event.get("observed_at") or "")) or utc_now()
    return root / "events" / observed.strftime("%Y-%m") / (
        str(event["event_id"]) + ".json")


def iter_event_paths(root: Path) -> Iterable[Path]:
    events = root / "events"
    if not events.exists():
        return []
    return sorted(events.glob("*/*.json"))


def read_event(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,
                      dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"invalid friction event: {path}")
    return data


def find_event(root: Path, event_id: str) -> tuple[Path, dict[str, Any]]:
    matches = list((root / "events").glob(f"*/{event_id}.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one event {event_id}, found {len(matches)}")
    return matches[0], read_event(matches[0])


def build_event(source_id: str, source_event_type: str, observed_at: str,
                classification: str, event_type: str, facts: dict[str, Any],
                evidence_refs: list[str], confidence: float, owner: dict[str,
                                                                         Any],
                now: datetime, actionable: bool | None = None,
                **extra: Any) -> dict[str, Any]:
    is_actionable = classification == "observed" if actionable is None else actionable
    event = {
        "schema_version":
            SCHEMA_VERSION,
        "event_id":
            canonical_event_id("codex_session", source_id, event_type,
                               evidence_refs),
        "source": {
            "kind": "codex_session",
            "session_id": source_id,
            "event_type": source_event_type,
        },
        "observed_at":
            observed_at,
        "classification":
            classification,
        "event_type":
            event_type,
        "facts":
            facts,
        "evidence_refs":
            sorted(evidence_refs),
        "confidence":
            confidence,
        "owner":
            owner,
        "lifecycle":
            "pending" if is_actionable else "deferred",
        "created_at":
            isoformat(now),
        "last_owner_seen_at":
            isoformat(now),
        "retention_class":
            "standard",
    }
    event.update(extra)
    return event


def write_event(root: Path, event: dict[str, Any]) -> tuple[Path, bool]:
    path = event_path(root, event)
    if path.exists():
        return path, False
    atomic_write_json(path, event)
    return path, True


def supersede_aggregate(root: Path, new_event: dict[str, Any],
                        now: datetime) -> int:
    count = 0
    new_path = str(new_event.get("facts", {}).get("path") or "")
    source_id = str(new_event.get("source", {}).get("session_id") or "")
    for path in iter_event_paths(root):
        event = read_event(path)
        if event.get("event_id") == new_event.get("event_id"):
            continue
        if event.get("event_type") != "repeated_file_edit_candidate":
            continue
        if event.get("source", {}).get("session_id") != source_id:
            continue
        if event.get("facts", {}).get("path") != new_path:
            continue
        if event.get("lifecycle") in SETTLED:
            continue
        current_owner = event.get("owner") if isinstance(
            event.get("owner"), dict) else {}
        if owner_key(current_owner) != "unclaimed":
            continue
        event["lifecycle"] = "resolved"
        event["resolution"] = "superseded"
        event["settled_at"] = isoformat(now)
        event["superseded_by"] = new_event["event_id"]
        event["settled_from"] = event.get("owner")
        event["owner"] = {"kind": "unclaimed", "id": None}
        atomic_write_json(path, event)
        append_rollup(root, event)
        count += 1
    return count


def collect_events(path: Path, root: Path, owner_spec: str,
                   now: datetime) -> dict[str, Any]:
    owner = owner_from_spec(owner_spec)
    source_id = ""
    cwd: str | None = None
    line_count = 0
    raw: list[tuple[int, dict[str, Any]]] = []

    with path.open(encoding="utf-8") as handle:
        for line_count, line in enumerate(handle, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            if record.get("type") == "session_meta":
                payload = record.get("payload")
                if isinstance(payload, dict):
                    source_id = str(
                        payload.get("session_id") or payload.get("id") or
                        source_id)
                    cwd = str(payload.get("cwd") or cwd or "") or None
            raw.append((line_count, record))

    if not source_id:
        raise ValueError("rollout has no session_meta session id")

    created: list[str] = []
    existing: list[str] = []
    successful_patches: dict[str, list[dict[str, str]]] = {}

    for line_number, record in raw:
        payload = record.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        outer_type = record.get("type")
        payload_type = payload.get("type")
        timestamp = str(record.get("timestamp") or isoformat(now))

        if ((outer_type == "event_msg" and payload_type == "turn_aborted") or
                outer_type == "turn_aborted"):
            turn_id = str(payload.get("turn_id") or f"line-{line_number}")
            evidence = [f"codex-session:{source_id}#turn:{turn_id}"]
            facts = {
                key: payload[key]
                for key in ("reason", "duration_ms")
                if key in payload
            }
            event = build_event(source_id, "turn_aborted", timestamp,
                                "observed", "task_aborted", facts, evidence,
                                1.0, owner, now, actionable=False,
                                candidate_limits=[
                                    "中断是客观事实，但不单独证明执行失败",
                                    "只有结合可避免的失败路线与后续 fallback 才可提升",
                                ])
            target, is_new = write_event(root, event)
            (created if is_new else existing).append(target.stem)

        if outer_type != "event_msg" or payload_type != "patch_apply_end":
            continue
        call_id = str(payload.get("call_id") or f"line-{line_number}")
        turn_id = str(payload.get("turn_id") or "")
        changes = payload.get("changes")
        paths = sorted(changes) if isinstance(changes, dict) else []
        normalized = [normalize_path(item, cwd) for item in paths]
        evidence = [f"codex-session:{source_id}#call:{call_id}"]
        success = payload.get("success") is True
        if not success:
            event = build_event(source_id, "patch_apply_end", timestamp,
                                "observed", "patch_failure", {
                                    "paths": normalized,
                                    "turn_id": turn_id,
                                }, evidence, 1.0, owner, now)
            target, is_new = write_event(root, event)
            (created if is_new else existing).append(target.stem)
            continue
        for item in normalized:
            successful_patches.setdefault(item, []).append({
                "call_id": call_id,
                "turn_id": turn_id,
                "timestamp": timestamp,
                "evidence": evidence[0],
            })

    superseded = 0
    for changed_path, patches in successful_patches.items():
        distinct_turns = {
            item["turn_id"] for item in patches if item["turn_id"]
        }
        if (len(patches) < MIN_REPEATED_PATCHES or
                len(distinct_turns) < MIN_REPEATED_TURNS):
            continue
        refs = sorted({item["evidence"] for item in patches})
        observed_at = max(item["timestamp"] for item in patches)
        event = build_event(
            source_id,
            "patch_apply_end",
            observed_at,
            "derived",
            "repeated_file_edit_candidate", {
                "path": changed_path,
                "successful_patch_count": len(patches),
                "distinct_turn_count": len(distinct_turns),
            },
            refs,
            0.7,
            owner,
            now,
            derivation={
                "successful_patch_count": "count(success == true)",
                "distinct_turn_count": "count(distinct turn_id)",
            },
            candidate_limits=[
                "事件跨多个 turn",
                "可能来自用户主动迭代",
                "不能直接判定为 agent 失败",
            ])
        target, is_new = write_event(root, event)
        if is_new:
            superseded += supersede_aggregate(root, event, now)
        (created if is_new else existing).append(target.stem)

    cursor = {
        "schema_version": "agent.friction.cursor.v0",
        "source_kind": "codex_session",
        "source_id": source_id,
        "rollout": str(path),
        "last_line": line_count,
        "source_size": path.stat().st_size,
        "updated_at": isoformat(now),
    }
    atomic_write_json(root / "cursors" / f"{source_id}.json", cursor)
    return {
        "source_id": source_id,
        "rollout": str(path),
        "created_event_ids": sorted(created),
        "existing_event_ids": sorted(existing),
        "superseded_events": superseded,
        "cursor": cursor,
    }


def checkpoint(root: Path, event_ids: list[str], owner_spec: str,
               now: datetime) -> dict[str, Any]:
    owner = owner_from_spec(owner_spec)
    if owner["kind"] == "unclaimed":
        raise ValueError("checkpoint owner cannot be unclaimed")
    updated = []
    for event_id in event_ids:
        path, event = find_event(root, event_id)
        if event.get("lifecycle") in SETTLED:
            raise ValueError(
                f"event {event_id} is already settled as {event.get('lifecycle')}"
            )
        current = event.get("owner") if isinstance(event.get("owner"),
                                                   dict) else {}
        if current.get("kind") not in {"unclaimed", owner["kind"]}:
            raise ValueError(
                f"event {event_id} already belongs to {owner_key(current)}")
        if current.get("kind") == owner["kind"] and current.get("id") not in {
                None, owner["id"]
        }:
            raise ValueError(
                f"event {event_id} already belongs to {owner_key(current)}")
        event["owner"] = owner
        event["last_owner_seen_at"] = isoformat(now)
        if (event.get("lifecycle") not in SETTLED and
                owner["kind"] == "ll_contract"):
            event["lifecycle"] = "claimed"
        atomic_write_json(path, event)
        updated.append(event_id)
    return {"owner": owner_key(owner), "checkpointed_event_ids": updated}


def claim(root: Path, from_owner_spec: str, contract: str,
          now: datetime) -> dict[str, Any]:
    from_owner = owner_from_spec(from_owner_spec)
    if from_owner["kind"] != "context":
        raise ValueError("claim source must be context:<abbr>:<route>")
    target = owner_from_spec(f"ll-contract:{contract}")
    claimed = []
    for path in iter_event_paths(root):
        event = read_event(path)
        if event.get("lifecycle") in SETTLED:
            continue
        current = event.get("owner") if isinstance(event.get("owner"),
                                                   dict) else {}
        if owner_key(current) != owner_key(from_owner):
            continue
        event["claimed_from"] = current
        event["owner"] = target
        event["lifecycle"] = "claimed"
        event["last_owner_seen_at"] = isoformat(now)
        atomic_write_json(path, event)
        claimed.append(event["event_id"])
    return {
        "from_owner": owner_key(from_owner),
        "to_owner": owner_key(target),
        "claimed_event_ids": sorted(claimed),
    }


def event_summary(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    current_owner = event.get("owner") if isinstance(event.get("owner"),
                                                      dict) else {}
    source = event.get("source") if isinstance(event.get("source"), dict) else {}
    return {
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "classification": event.get("classification"),
        "lifecycle": event.get("lifecycle"),
        "owner": owner_key(current_owner),
        "source_id": source.get("session_id"),
        "facts": event.get("facts"),
        "path": str(path),
    }


def list_events(root: Path, owner_spec: str | None,
                lifecycles: set[str], source_id: str | None = None) -> dict[str, Any]:
    expected_owner = owner_key(
        owner_from_spec(owner_spec)) if owner_spec else ""
    rows = []
    for path in iter_event_paths(root):
        event = read_event(path)
        current_owner = event.get("owner") if isinstance(
            event.get("owner"), dict) else {}
        if expected_owner and owner_key(current_owner) != expected_owner:
            continue
        source = event.get("source") if isinstance(event.get("source"), dict) else {}
        if source_id and source.get("session_id") != source_id:
            continue
        if lifecycles and event.get("lifecycle") not in lifecycles:
            continue
        rows.append(event_summary(path, event))
    return {"count": len(rows), "events": rows}


def open_summary(inbox: Path, limit: int) -> dict[str, Any]:
    if limit < 1 or limit > 50:
        raise ValueError("--limit must be between 1 and 50")

    entries: list[dict[str, Any]] = []
    in_open = False
    current: dict[str, Any] | None = None
    for line in inbox.read_text(encoding="utf-8").splitlines():
        if line == "## Open":
            in_open = True
            continue
        if in_open and line.startswith("## "):
            break
        if not in_open:
            continue
        if line.startswith("### "):
            if current:
                entries.append(current)
            current = {"title": line.removeprefix("### ").strip()}
            continue
        if current is None:
            continue
        if line.startswith("- Signature："):
            current["signature"] = line.removeprefix("- Signature：").strip()
        elif line.startswith("- Occurrence："):
            current["bound_occurrence_count"] = int(
                current.get("bound_occurrence_count", 0)
            ) + 1
        elif line.startswith("- 复现："):
            match = re.match(r"^- 复现：\+?(\d+)", line)
            if not match:
                raise ValueError(f"invalid recurrence line: {line}")
            current["recurrence"] = int(match.group(1))
        elif line.startswith("- 障碍："):
            summary = line.removeprefix("- 障碍：").strip()
            first_sentence, separator, _ = summary.partition("。")
            if separator and len(first_sentence) < 160:
                current["summary"] = first_sentence + separator
            elif len(summary) > 160:
                current["summary"] = summary[:159].rstrip() + "…"
            else:
                current["summary"] = summary
    if current:
        entries.append(current)

    visible = [
        entry for entry in entries
        if entry.get("signature") and entry.get("summary")
    ][:limit]
    for entry in visible:
        recurrence = int(entry.get("recurrence", 0))
        occurrence_count = recurrence + 1
        bound_count = int(entry.pop("bound_occurrence_count", 0))
        entry["recurrence"] = recurrence
        entry["occurrence_count"] = occurrence_count
        if bound_count == occurrence_count:
            entry["identity_status"] = "bound"
        elif bound_count == 0:
            entry["identity_status"] = "legacy_unbound"
        else:
            entry["identity_status"] = "incomplete"
    return {
        "open_count": len(entries),
        "shown": len(visible),
        "limit": limit,
        "entries": visible,
    }


def codex_thread_project_occurrence_key(thread_id: str, project_cwd: str) -> str:
    identity = json.dumps(
        {"project_cwd": project_cwd, "thread_id": thread_id},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "codex-thread-project:" + hashlib.sha256(identity.encode()).hexdigest()


def promoted_occurrence(settlement_path: Path,
                        signature: str) -> tuple[str, dict[str, str], str]:
    settlement = json.loads(settlement_path.read_text(encoding="utf-8"))
    if not isinstance(settlement, dict) or settlement.get(
            "schema") != "save-context.audit-settlement.v1":
        raise ValueError(f"invalid save-context settlement: {settlement_path}")
    if settlement.get("status") != "settled":
        raise ValueError(f"save-context settlement is not settled: {settlement_path}")
    items = settlement.get("items")
    if not isinstance(items, list):
        raise ValueError(f"settlement has no items: {settlement_path}")
    matches = [
        item for item in items
        if isinstance(item, dict)
        and item.get("disposition") == "promoted"
        and item.get("destination") == "global_friction"
        and item.get("signature") == signature
    ]
    if not matches:
        raise ValueError(
            f"no promoted global friction matches signature {signature}"
        )
    durable_refs = [item.get("durable_ref") for item in matches]
    if not all(isinstance(ref, str) and ref for ref in durable_refs) or len(
        set(durable_refs)
    ) != 1:
        raise ValueError(
            f"promoted items for {signature} do not share one durable_ref"
        )
    durable_ref = durable_refs[0]
    occurrence = settlement.get("occurrence")
    audit_id = settlement.get("audit_id")
    if not isinstance(occurrence, dict) or not all(
        isinstance(occurrence.get(field), str) and occurrence[field]
        for field in ("kind", "key", "thread_id", "project_cwd")
    ):
        raise ValueError("settlement occurrence identity is incomplete")
    if occurrence["kind"] != "codex_thread_project":
        raise ValueError("unsupported promoted occurrence kind")
    expected_key = codex_thread_project_occurrence_key(
        occurrence["thread_id"], occurrence["project_cwd"]
    )
    if occurrence["key"] != expected_key:
        raise ValueError("promoted occurrence key does not match its identity")
    if not isinstance(audit_id, str) or not audit_id:
        raise ValueError("settlement is missing audit_id")
    return durable_ref, occurrence, audit_id


def open_entry_bounds(lines: list[str], signature: str) -> tuple[int, int]:
    try:
        open_start = lines.index("## Open") + 1
    except ValueError as error:
        raise ValueError("friction inbox is missing ## Open") from error
    open_end = next(
        (index for index in range(open_start, len(lines))
         if lines[index].startswith("## ")),
        len(lines),
    )
    starts = [
        index for index in range(open_start, open_end)
        if lines[index].startswith("### ")
    ]
    matches: list[tuple[int, int]] = []
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else open_end
        if f"- Signature：{signature}" in lines[start:end]:
            matches.append((start, end))
    if len(matches) != 1:
        raise ValueError(
            f"expected one Open friction with signature {signature}, found {len(matches)}"
        )
    return matches[0]


def occurrence_payload(line: str) -> dict[str, str]:
    prefix = "- Occurrence："
    try:
        payload = json.loads(line.removeprefix(prefix))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid occurrence line: {line}") from error
    if not isinstance(payload, dict) or not all(
        isinstance(payload.get(field), str) and payload[field]
        for field in ("key", "thread_id", "project_cwd", "evidence")
    ):
        raise ValueError(f"incomplete occurrence line: {line}")
    expected_key = codex_thread_project_occurrence_key(
        payload["thread_id"], payload["project_cwd"]
    )
    if payload["key"] != expected_key:
        raise ValueError(f"occurrence key does not match its identity: {line}")
    return payload


def record_occurrence(inbox: Path, settlement_path: Path,
                      signature: str, initialize: bool = False) -> dict[str, Any]:
    inbox = inbox.resolve()
    # Lock a stable sidecar: atomic replacement changes the inbox inode.
    with inbox.with_name(inbox.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _record_occurrence_locked(inbox, settlement_path, signature, initialize)


def _record_occurrence_locked(inbox: Path, settlement_path: Path,
                             signature: str, initialize: bool) -> dict[str, Any]:
    durable_ref, occurrence, audit_id = promoted_occurrence(
        settlement_path.resolve(), signature)
    durable_path, separator, _ = durable_ref.rpartition("#")
    if not separator or Path(durable_path).expanduser().resolve() != inbox.resolve():
        raise ValueError(
            f"promoted occurrence durable_ref does not target inbox: {durable_ref}"
        )

    original = inbox.read_text(encoding="utf-8")
    lines = original.splitlines()
    start, end = open_entry_bounds(lines, signature)
    occurrence_lines = [
        line for line in lines[start:end] if line.startswith("- Occurrence：")
    ]
    occurrences = [occurrence_payload(line) for line in occurrence_lines]
    existing_keys = {item["key"] for item in occurrences}
    if len(existing_keys) != len(occurrences):
        raise ValueError(f"duplicate occurrence identities for signature {signature}")
    recurrence_indexes = [
        index for index in range(start, end)
        if lines[index].startswith("- 复现：")
    ]
    if len(recurrence_indexes) > 1:
        raise ValueError(f"multiple recurrence lines for signature {signature}")
    if recurrence_indexes:
        match = re.match(r"^- 复现：\+?(\d+)", lines[recurrence_indexes[0]])
        if not match:
            raise ValueError(
                f"invalid recurrence line for signature {signature}"
            )
        if not occurrences:
            raise ValueError(
                f"legacy recurrence for {signature} has no occurrence identities"
            )
        if int(match.group(1)) != len(occurrences) - 1:
            raise ValueError(
                f"recurrence count does not match occurrence identities for {signature}"
            )
    if occurrence["key"] in existing_keys:
        return {
            "signature": signature,
            "occurrence_key": occurrence["key"],
            "occurrence_count": len(occurrences),
            "recurrence": max(len(occurrences) - 1, 0),
            "updated": False,
        }
    if not occurrences and not initialize:
        raise ValueError(
            f"friction {signature} has no occurrence identity; migrate it or use "
            "--initialize only when creating a new entry"
        )
    if occurrences and initialize:
        raise ValueError(
            f"--initialize is only valid for a new friction occurrence history: {signature}"
        )

    payload = {
        "key": occurrence["key"],
        "thread_id": occurrence["thread_id"],
        "project_cwd": occurrence["project_cwd"],
        "evidence": f"save-context-audit:{audit_id}",
    }
    occurrence_line = "- Occurrence：" + json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    insert_at = recurrence_indexes[0] if recurrence_indexes else next(
        (index for index in range(start, end)
         if lines[index].startswith("- 状态：")),
        end,
    )
    lines.insert(insert_at, occurrence_line)
    occurrence_count = len(occurrences) + 1
    recurrence = occurrence_count - 1
    if recurrence:
        recurrence_line = (
            f"- 复现：+{recurrence}（最近：save-context-audit:{audit_id}）"
        )
        recurrence_index = next(
            (index for index in range(start, end + 1)
             if lines[index].startswith("- 复现：")),
            None,
        )
        if recurrence_index is None:
            status_index = next(
                (index for index in range(start, end + 1)
                 if lines[index].startswith("- 状态：")),
                end + 1,
            )
            lines.insert(status_index, recurrence_line)
        else:
            lines[recurrence_index] = recurrence_line
    atomic_write_text(inbox, "\n".join(lines) + ("\n" if original.endswith("\n") else ""))
    return {
        "signature": signature,
        "occurrence_key": occurrence["key"],
        "occurrence_count": occurrence_count,
        "recurrence": recurrence,
        "updated": True,
    }


def status_events(root: Path, owner_spec: str) -> dict[str, Any]:
    expected_owner = owner_key(owner_from_spec(owner_spec))
    by_lifecycle: dict[str, int] = {}
    by_event_type: dict[str, int] = {}
    for path in iter_event_paths(root):
        event = read_event(path)
        current_owner = event.get("owner") if isinstance(
            event.get("owner"), dict) else {}
        if owner_key(current_owner) != expected_owner:
            continue
        lifecycle = str(event.get("lifecycle") or "unknown")
        event_type = str(event.get("event_type") or "unknown")
        by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
        by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
    actionable = sum(
        by_lifecycle.get(item, 0) for item in ("pending", "claimed"))
    return {
        "owner": expected_owner,
        "actionable_count": actionable,
        "by_lifecycle": dict(sorted(by_lifecycle.items())),
        "by_event_type": dict(sorted(by_event_type.items())),
    }


def append_rollup(root: Path, event: dict[str, Any]) -> Path:
    settled = parse_time(str(event.get("settled_at") or "")) or utc_now()
    path = root / "rollups" / f"{settled:%Y-%m}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "resolution": event["lifecycle"],
        "source_kind": event.get("source", {}).get("kind"),
        "settled_at": event["settled_at"],
        "retention_class": event.get("retention_class", "standard"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def settle(root: Path, event_id: str, resolution: str, dry_run: bool,
           label: str | None, reason: str | None, interpreter: str,
           incident: bool, expected_owner_spec: str,
           now: datetime) -> dict[str, Any]:
    if resolution not in RESOLUTIONS:
        raise ValueError(f"unsupported resolution: {resolution}")
    path, event = find_event(root, event_id)
    expected_owner = owner_key(owner_from_spec(expected_owner_spec))
    current_owner = event.get("owner") if isinstance(event.get("owner"),
                                                     dict) else {}
    if owner_key(current_owner) != expected_owner:
        raise ValueError(
            f"event {event_id} belongs to {owner_key(current_owner)}, not {expected_owner}"
        )
    if event.get("lifecycle") in SETTLED:
        raise ValueError(
            f"event {event_id} is already settled as {event.get('lifecycle')}")
    proposed = json.loads(json.dumps(event))
    proposed["lifecycle"] = resolution
    if label:
        if not reason:
            raise ValueError("--reason is required with --label")
        proposed["interpretation"] = {
            "label": label,
            "interpreter": {
                "kind": interpreter,
                "id": "operator"
            },
            "evidence_refs": proposed.get("evidence_refs", []),
            "confidence": 1.0 if interpreter == "human" else 0.7,
            "reason": reason,
            "interpreted_at": isoformat(now),
        }
    if incident:
        proposed["retention_class"] = "incident"
    if resolution in SETTLED:
        proposed["settled_at"] = isoformat(now)
        proposed["settled_from"] = proposed.get("owner")
        proposed["owner"] = {"kind": "unclaimed", "id": None}
    else:
        proposed["last_owner_seen_at"] = isoformat(now)

    result = {
        "event_id": event_id,
        "resolution": resolution,
        "event_path": str(path),
        "dry_run": dry_run,
        "promotion_candidate": resolution == "promoted",
    }
    if dry_run:
        result["proposed_event"] = proposed
        return result
    atomic_write_json(path, proposed)
    if resolution in SETTLED:
        result["rollup_path"] = str(append_rollup(root, proposed))
    return result


def owner_is_active(owner: dict[str, Any], ai_home: Path) -> bool:
    kind = owner.get("kind")
    owner_id = owner.get("id")
    if kind == "ll_contract" and isinstance(owner_id, str):
        path = Path(owner_id).expanduser()
        if not path.is_file():
            return False
        try:
            contract = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True
        return contract.get("ll_contract", {}).get("exit",
                                                   {}).get("state") == "active"
    if kind == "context" and isinstance(owner_id, str):
        abbr, route = owner_id.split(":", 1)
        path = ai_home / "contexts" / f"{abbr}.md"
        if not path.is_file():
            return False
        try:
            import yaml  # type: ignore[import-not-found]

            lines = path.read_text(encoding="utf-8").splitlines()
            delimiters = [
                index for index, line in enumerate(lines)
                if line.strip() == "---"
            ]
            if len(delimiters) < 2:
                return True
            data = yaml.safe_load("\n".join(lines[delimiters[0] +
                                                  1:delimiters[1]]))
            if not isinstance(data, dict):
                return True
            if route == "mainline":
                item = data.get("mainline")
            else:
                workstreams = data.get("workstreams")
                item = workstreams.get(route) if isinstance(workstreams,
                                                            dict) else None
            if not isinstance(item, dict):
                return False
            return item.get("state") in {
                "active", "blocked", "parked", "closure-candidate"
            }
        except (ImportError, OSError, ValueError):
            return True
    return False


def rollup_contains(root: Path, event_id: str) -> bool:
    rollups = root / "rollups"
    if not rollups.exists():
        return False
    for path in rollups.glob("*.jsonl"):
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(row,
                                  dict) and row.get("event_id") == event_id:
                        return True
        except OSError:
            continue
    return False


def cleanup_dry_run(root: Path, ai_home: Path, now: datetime) -> dict[str, Any]:
    delete_paths = []
    protected_paths = []
    orphan_review_paths = []
    for path in iter_event_paths(root):
        event = read_event(path)
        lifecycle = str(event.get("lifecycle") or "")
        owner = event.get("owner") if isinstance(event.get("owner"),
                                                 dict) else {}
        if owner_is_active(owner, ai_home):
            protected_paths.append(str(path))
            continue
        if lifecycle in SETTLED:
            start = parse_time(str(event.get("settled_at") or ""))
            ttl = 90 if event.get("retention_class") == "incident" else 30
            if start and (now - start).days >= ttl:
                if rollup_contains(root, str(event.get("event_id") or "")):
                    delete_paths.append(str(path))
                else:
                    protected_paths.append(str(path))
            continue
        seen = parse_time(str(event.get("last_owner_seen_at") or ""))
        if seen and (now - seen).days >= 30:
            orphan_review_paths.append(str(path))
    return {
        "dry_run": True,
        "delete_paths": sorted(delete_paths),
        "orphan_review_paths": sorted(orphan_review_paths),
        "protected_paths": sorted(protected_paths),
    }


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect and manage objective agent-friction events")
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--ai-home", type=Path, default=Path.home() / ".ai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    collect.add_argument("--rollout")
    collect.add_argument("--thread-id")
    collect.add_argument("--details", action="store_true")
    collect.add_argument("--codex-home",
                         type=Path,
                         default=Path.home() / ".codex")

    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("--owner", required=True)
    checkpoint_parser.add_argument("--event-id", action="append", required=True)

    claim_parser = subparsers.add_parser("claim")
    claim_parser.add_argument("--from-owner", required=True)
    claim_parser.add_argument("--contract", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--owner")
    list_parser.add_argument("--lifecycle", action="append", default=[])
    list_parser.add_argument("--source-id", "--thread-id", dest="source_id")

    summary_parser = subparsers.add_parser("open-summary")
    summary_parser.add_argument("--inbox", type=Path, default=default_inbox())
    summary_parser.add_argument("--limit", type=int, default=8)

    record_parser = subparsers.add_parser("record-occurrence")
    record_parser.add_argument("--inbox", type=Path, default=default_inbox())
    record_parser.add_argument("--settlement", type=Path, required=True)
    record_parser.add_argument("--signature", required=True)
    record_parser.add_argument("--initialize", action="store_true")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--owner", required=True)

    settle_parser = subparsers.add_parser("settle")
    settle_parser.add_argument("--event-id", required=True)
    settle_parser.add_argument("--resolution",
                               choices=sorted(RESOLUTIONS),
                               required=True)
    settle_parser.add_argument("--expect-owner", required=True)
    settle_parser.add_argument("--dry-run", action="store_true")
    settle_parser.add_argument("--label")
    settle_parser.add_argument("--reason")
    settle_parser.add_argument("--interpreter",
                               choices=["human", "llm"],
                               default="human")
    settle_parser.add_argument("--incident", action="store_true")

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--dry-run", action="store_true", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    now = utc_now()
    try:
        if args.command == "collect":
            rollout = locate_rollout(args.codex_home, args.rollout,
                                     args.thread_id)
            result = collect_events(rollout, args.root, "unclaimed", now)
            if args.details:
                result["events"] = [
                    event_summary(*find_event(args.root, event_id))
                    for event_id in result["created_event_ids"] +
                    result["existing_event_ids"]
                ]
        elif args.command == "checkpoint":
            result = checkpoint(args.root, args.event_id, args.owner, now)
        elif args.command == "claim":
            result = claim(args.root, args.from_owner, args.contract, now)
        elif args.command == "list":
            result = list_events(args.root, args.owner, set(args.lifecycle or
                                                            []), args.source_id)
        elif args.command == "open-summary":
            result = open_summary(args.inbox, args.limit)
        elif args.command == "record-occurrence":
            result = record_occurrence(args.inbox, args.settlement,
                                       args.signature, args.initialize)
        elif args.command == "status":
            result = status_events(args.root, args.owner)
        elif args.command == "settle":
            result = settle(args.root, args.event_id, args.resolution,
                            args.dry_run, args.label, args.reason,
                            args.interpreter, args.incident, args.expect_owner,
                            now)
        elif args.command == "cleanup":
            result = cleanup_dry_run(args.root, args.ai_home, now)
        else:
            parser.error(f"unsupported command: {args.command}")
            return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
