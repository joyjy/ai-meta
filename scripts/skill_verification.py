#!/usr/bin/env python3
"""Track revision-bound verification evidence for skill changes."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterator

SCHEMA = "skill.verification.v1"
SUMMARY_SCHEMA = "skill.verification.summary.v1"
CHANGE_ID_RE = re.compile(r"^[a-f0-9]{16}$")
CHECK_STATES = {"passed", "failed"}
SAMPLE_RESULTS = {"passed", "failed", "inconclusive"}
OPEN_VERDICTS = {"pending", "inconclusive"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_time(value: str | None) -> str:
    if not value:
        return utc_now()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def require_text(value: str, name: str, limit: int = 1000) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > limit:
        raise ValueError(f"{name} exceeds {limit} characters")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(payload: dict[str, Any], length: int = 16) -> str:
    encoded = json.dumps(payload,
                         ensure_ascii=False,
                         sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args],
                            text=True,
                            capture_output=True,
                            check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def resolve_skill_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_dir():
        path = path / "SKILL.md"
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"skill path is not readable: {path}") from exc
    if resolved.name != "SKILL.md" or not resolved.is_file():
        raise ValueError("skill path must resolve to a SKILL.md file")
    return resolved


def resolve_artifact_path(value: str, repo: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo / path
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repo)
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"artifact must be a readable file inside {repo}: {value}"
        ) from exc
    if not resolved.is_file():
        raise ValueError(f"artifact must be a readable file: {resolved}")
    return resolved


def source_identity(skill_path: Path,
                    artifact_values: list[str]) -> dict[str, Any]:
    repo_text = run_git(skill_path.parent, "rev-parse", "--show-toplevel")
    repo = Path(repo_text).resolve()
    relative = str(skill_path.relative_to(repo))
    reference_paths: set[Path] = set()
    for value in artifact_values:
        artifact = resolve_artifact_path(value, repo)
        if artifact != skill_path:
            reference_paths.add(artifact)
    artifact_paths = [skill_path, *sorted(reference_paths, key=str)]
    artifacts = [
        {
            "relative_path": str(path.relative_to(repo)),
            "content_sha256": sha256_file(path),
        }
        for path in artifact_paths
    ]
    revision = run_git(repo, "rev-parse", "HEAD")
    dirty = bool(run_git(
        repo, "status", "--porcelain", "--",
        *(item["relative_path"] for item in artifacts),
    ))
    content_sha256 = artifacts[0]["content_sha256"]
    source_fingerprint = content_sha256
    if len(artifacts) > 1:
        source_fingerprint = hashlib.sha256(json.dumps(
            artifacts, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
    revision_identity = (f"working-tree:{revision}:{source_fingerprint[:12]}"
                         if dirty else revision)
    return {
        "owner_repo": str(repo),
        "relative_path": relative,
        "git_revision": revision,
        "dirty": dirty,
        "content_sha256": content_sha256,
        "source_fingerprint": source_fingerprint,
        "artifacts": artifacts,
        "revision_identity": revision_identity,
    }


def default_root() -> Path:
    return Path.home() / ".ai" / "skill-verification"


def change_path(root: Path, change_id: str) -> Path:
    if not CHANGE_ID_RE.fullmatch(change_id):
        raise ValueError(f"invalid change id: {change_id!r}")
    return root / "changes" / f"{change_id}.json"


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w",
                            encoding="utf-8",
                            dir=path.parent,
                            delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


@contextmanager
def locked(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".lock"
    with lock_path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_change(root: Path, change_id: str) -> tuple[Path, dict[str, Any]]:
    path = change_path(root, change_id)
    if not path.exists():
        raise ValueError(f"skill verification change not found: {change_id}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid skill verification record: {path}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError(f"invalid skill verification record: {path}")
    if data.get("change_id") != change_id:
        raise ValueError(f"change id does not match record path: {path}")
    return path, data


def latest_checks(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for check in record.get("checks", []):
        if isinstance(check, dict) and isinstance(check.get("name"), str):
            latest[check["name"]] = check
    return latest


def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    checks = latest_checks(record)
    passed_checks = sum(item.get("status") == "passed"
                         for item in checks.values())
    failed_checks = sorted(name for name, item in checks.items()
                           if item.get("status") == "failed")
    required_samples = int(record.get("contract", {}).get(
        "required_samples", 0))
    matching_loads = {
        item.get("load_id")
        for item in record.get("loads", [])
        if isinstance(item, dict) and item.get("matches_change") is True
    }
    samples = [
        item for item in record.get("samples", [])
        if isinstance(item, dict) and item.get("load_id") in matching_loads
    ]
    passed_samples = sum(item.get("result") == "passed" for item in samples)
    failed_samples = [
        str(item.get("sample_id")) for item in samples
        if item.get("result") == "failed"
    ]

    if failed_checks:
        verdict, reason = "falsified", "latest_check_failed"
    elif failed_samples:
        verdict, reason = "falsified", "post_load_sample_failed"
    elif not checks:
        verdict, reason = "pending", "no_static_check"
    elif required_samples == 0:
        verdict, reason = "static_validated", "all_latest_checks_passed"
    elif passed_samples >= required_samples:
        verdict, reason = "validated", "required_post_load_samples_passed"
    elif samples:
        verdict, reason = "inconclusive", "post_load_samples_incomplete"
    else:
        verdict, reason = "pending", "no_post_load_sample"

    return {
        "verdict": verdict,
        "reason": reason,
        "latest_checks": len(checks),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "matching_loads": len(matching_loads),
        "passed_samples": passed_samples,
        "failed_samples": failed_samples,
        "required_samples": required_samples,
    }


def refresh(record: dict[str, Any], updated_at: str) -> None:
    record["evaluation"] = evaluate(record)
    record["updated_at"] = updated_at


def append_unique(items: list[dict[str, Any]], item: dict[str, Any],
                  identity_key: str) -> bool:
    if any(existing.get(identity_key) == item.get(identity_key)
           for existing in items if isinstance(existing, dict)):
        return False
    items.append(item)
    return True


def begin(args: argparse.Namespace) -> dict[str, Any]:
    skill_path = resolve_skill_path(args.skill)
    source = source_identity(skill_path, args.artifact)
    acceptance = [require_text(item, "acceptance", 500)
                  for item in args.acceptance]
    if args.required_samples < 0:
        raise ValueError("required samples must be zero or greater")
    summary = require_text(args.summary, "summary", 500)
    identity = {
        "canonical_path": str(skill_path),
        "content_sha256": source["source_fingerprint"],
        "summary": summary,
        "acceptance": acceptance,
        "required_samples": args.required_samples,
    }
    change_id = stable_id(identity)
    path = change_path(args.root, change_id)
    created_at = normalized_time(args.at)
    record = {
        "schema": SCHEMA,
        "change_id": change_id,
        "skill": {
            "skill_id": skill_path.parent.name,
            "canonical_path": str(skill_path),
        },
        "source": source,
        "contract": {
            "summary": summary,
            "acceptance": acceptance,
            "required_samples": args.required_samples,
        },
        "checks": [],
        "loads": [],
        "samples": [],
        "created_at": created_at,
    }
    refresh(record, created_at)
    with locked(args.root):
        if path.exists():
            _, existing = load_change(args.root, change_id)
            return existing
        atomic_write_json(path, record)
    return record


def record_check(args: argparse.Namespace) -> dict[str, Any]:
    if args.status not in CHECK_STATES:
        raise ValueError(f"unsupported check status: {args.status}")
    recorded_at = normalized_time(args.at)
    name = require_text(args.name, "check name", 200)
    evidence_ref = require_text(args.evidence_ref, "evidence ref")
    event = {
        "check_id": stable_id({
            "change_id": args.change_id,
            "name": name,
            "status": args.status,
            "evidence_ref": evidence_ref,
        }),
        "name": name,
        "status": args.status,
        "evidence_ref": evidence_ref,
        "recorded_at": recorded_at,
    }
    with locked(args.root):
        path, record = load_change(args.root, args.change_id)
        append_unique(record["checks"], event, "check_id")
        refresh(record, recorded_at)
        atomic_write_json(path, record)
    return record


def record_load(args: argparse.Namespace) -> dict[str, Any]:
    loaded_path = resolve_skill_path(args.loaded_path)
    loaded_digest = sha256_file(loaded_path)
    loaded_at = normalized_time(args.at)
    client = require_text(args.client, "client", 100)
    session_id = require_text(args.session_id, "session id", 300)
    with locked(args.root):
        path, record = load_change(args.root, args.change_id)
        expected_digest = record["source"]["content_sha256"]
        if loaded_digest != expected_digest:
            raise ValueError(
                "loaded skill content does not match the change fingerprint")
        for artifact in record["source"]["artifacts"]:
            artifact_path = resolve_artifact_path(
                artifact["relative_path"], Path(record["source"]["owner_repo"]))
            if sha256_file(artifact_path) != artifact["content_sha256"]:
                raise ValueError(
                    "loaded artifact content does not match the change fingerprint: "
                    + artifact["relative_path"])
        load_id = stable_id({
            "change_id": args.change_id,
            "client": client,
            "session_id": session_id,
            "loaded_path": str(loaded_path),
            "content_sha256": loaded_digest,
        })
        event = {
            "load_id": load_id,
            "client": client,
            "session_id": session_id,
            "loaded_path": str(loaded_path),
            "content_sha256": loaded_digest,
            "matches_change": True,
            "evidence_ref": (require_text(args.evidence_ref, "evidence ref")
                             if args.evidence_ref else None),
            "loaded_at": loaded_at,
        }
        append_unique(record["loads"], event, "load_id")
        refresh(record, loaded_at)
        atomic_write_json(path, record)
    return {"change_id": args.change_id, "load": event,
            "evaluation": record["evaluation"]}


def record_sample(args: argparse.Namespace) -> dict[str, Any]:
    if args.result not in SAMPLE_RESULTS:
        raise ValueError(f"unsupported sample result: {args.result}")
    observed_at = normalized_time(args.at)
    evidence_ref = require_text(args.evidence_ref, "evidence ref")
    note = require_text(args.note, "note") if args.note else None
    with locked(args.root):
        path, record = load_change(args.root, args.change_id)
        load_ids = {
            item.get("load_id") for item in record["loads"]
            if isinstance(item, dict) and item.get("matches_change") is True
        }
        if args.load_id not in load_ids:
            raise ValueError(
                f"matching load receipt not found: {args.load_id!r}")
        sample_id = stable_id({
            "change_id": args.change_id,
            "load_id": args.load_id,
            "result": args.result,
            "evidence_ref": evidence_ref,
        })
        event = {
            "sample_id": sample_id,
            "load_id": args.load_id,
            "result": args.result,
            "evidence_ref": evidence_ref,
            "note": note,
            "observed_at": observed_at,
        }
        append_unique(record["samples"], event, "sample_id")
        refresh(record, observed_at)
        atomic_write_json(path, record)
    return record


def compact(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "change_id": record["change_id"],
        "skill_id": record["skill"]["skill_id"],
        "canonical_path": record["skill"]["canonical_path"],
        "revision_identity": record["source"]["revision_identity"],
        "summary": record["contract"]["summary"],
        "acceptance": record["contract"]["acceptance"],
        "evaluation": evaluate(record),
        "updated_at": record.get("updated_at"),
    }


def status(args: argparse.Namespace) -> dict[str, Any]:
    if args.change_id:
        _, record = load_change(args.root, args.change_id)
        record["evaluation"] = evaluate(record)
        return record
    records = []
    for path in sorted((args.root / "changes").glob("*.json")):
        _, record = load_change(args.root, path.stem)
        summary = compact(record)
        if args.open_only and summary["evaluation"]["verdict"] not in OPEN_VERDICTS:
            continue
        records.append(summary)
    records.sort(key=lambda item: str(item.get("updated_at") or ""),
                 reverse=True)
    records = records[:args.limit]
    counts: dict[str, int] = {}
    for item in records:
        verdict = item["evaluation"]["verdict"]
        counts[verdict] = counts.get(verdict, 0) + 1
    return {
        "schema": SUMMARY_SCHEMA,
        "generated_at": utc_now(),
        "open_only": args.open_only,
        "counts": counts,
        "changes": records,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track verification evidence for revision-bound skill changes")
    parser.add_argument("--root", type=Path, default=default_root())
    commands = parser.add_subparsers(dest="command", required=True)

    begin_parser = commands.add_parser("begin")
    begin_parser.add_argument("--skill", required=True)
    begin_parser.add_argument("--summary", required=True)
    begin_parser.add_argument("--acceptance", action="append", required=True)
    begin_parser.add_argument("--artifact", action="append", default=[])
    begin_parser.add_argument("--required-samples", type=int, required=True)
    begin_parser.add_argument("--at")
    begin_parser.set_defaults(handler=begin)

    check_parser = commands.add_parser("check")
    check_parser.add_argument("--change-id", required=True)
    check_parser.add_argument("--name", required=True)
    check_parser.add_argument("--status", choices=sorted(CHECK_STATES), required=True)
    check_parser.add_argument("--evidence-ref", required=True)
    check_parser.add_argument("--at")
    check_parser.set_defaults(handler=record_check)

    load_parser = commands.add_parser("load")
    load_parser.add_argument("--change-id", required=True)
    load_parser.add_argument("--client", required=True)
    load_parser.add_argument("--session-id", required=True)
    load_parser.add_argument("--loaded-path", required=True)
    load_parser.add_argument("--evidence-ref")
    load_parser.add_argument("--at")
    load_parser.set_defaults(handler=record_load)

    sample_parser = commands.add_parser("sample")
    sample_parser.add_argument("--change-id", required=True)
    sample_parser.add_argument("--load-id", required=True)
    sample_parser.add_argument("--result", choices=sorted(SAMPLE_RESULTS), required=True)
    sample_parser.add_argument("--evidence-ref", required=True)
    sample_parser.add_argument("--note")
    sample_parser.add_argument("--at")
    sample_parser.set_defaults(handler=record_sample)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("--change-id")
    status_parser.add_argument("--open", dest="open_only", action="store_true")
    status_parser.add_argument("--limit", type=int, default=50)
    status_parser.set_defaults(handler=status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = args.root.expanduser()
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be positive")
    try:
        result = args.handler(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
