#!/usr/bin/env python3
"""Dispatch a save-context audit to Rollerskate without waiting for completion."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

import save_context_recover
from save_context_audit_archive import (
    ARCHIVE_DIRECTORY, archive_paths, archived_runs, ensure_bundle, path_size,
)
from save_context_audit_io import parse_json_object, run, write_text_atomic


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RS = Path.home() / "Documents/me/Projects/rollerskate/scripts/rs"
DEFAULT_AUDIT_ROOT = Path.home() / ".ai/audits/save-context"
WORKER_INSTRUCTIONS = (
    REPO_ROOT / "skills/save-context/references/agent-audit-worker.md"
)
SETTLEMENT_SCHEMA = "save-context.audit-settlement.v1"
SETTLEMENT_NAME = "settlement.json"
INSPECTION_SCHEMA = "save-context.audit-inspection.v1"
INSPECTION_NAME = "inspection.json"
DISPATCH_CONTRACT_REVISION = (
    "run-intent-owner-compiled-v4-runtime-selected-participant"
)
AUDIT_SUMMARY_SCHEMA = "save-context.audit-summary.v1"
AUDIT_SUMMARY_NAME = "audit-summary.json"
DISPOSITIONS = {"promoted", "resolved", "ignored", "deferred"}
TERMINAL_FAILURES = {"failed", "cancelled", "aborted"}


def audit_identity(
    packet: str,
    route: str,
    ll_path: Path | None,
) -> str:
    material = [
        DISPATCH_CONTRACT_REVISION,
        packet,
        route,
        "participant-policy:runtime-selected",
        WORKER_INSTRUCTIONS.read_text(encoding="utf-8"),
    ]
    if ll_path is not None:
        material.extend([
            str(ll_path.resolve()),
            ll_path.read_text(encoding="utf-8"),
        ])
    return hashlib.sha256("\n".join(material).encode()).hexdigest()[:20]


def packet_thread_id(packet: str, fallback: str) -> str:
    match = re.search(r"(?m)^- session_id: `([^`]+)`$", packet)
    return match.group(1) if match else fallback


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def initialize_workspace(
    workspace: Path,
    packet: str,
    project_cwd: Path,
    route: str,
    thread_id: str,
    ll_path: Path | None,
) -> None:
    workspace.mkdir(parents=True)
    shutil.copy2(WORKER_INSTRUCTIONS, workspace / "AUDITOR.md")
    write_text(workspace / "recovery-packet.md", packet)
    if ll_path is not None:
        shutil.copy2(ll_path, workspace / "effective-ll.md")

    ll_instruction = (
        "Read `effective-ll.md` as the exact effective LL contract."
        if ll_path is not None
        else "No LL contract is bound to this audit."
    )
    write_text(
        workspace / "AUDIT_TASK.md",
        "\n".join([
            "# Save-context audit task",
            "",
            f"- thread_id: `{thread_id}`",
            f"- project_cwd: `{project_cwd}`",
            f"- route: `{route}`",
            "- output_file: `agent-audit.yaml`",
            f"- summary_file: `{AUDIT_SUMMARY_NAME}`",
            "",
            "Follow `AUDITOR.md` and use `recovery-packet.md` as the only rollout",
            "evidence surface. Omit candidates that this bounded packet cannot prove.",
            ll_instruction,
            "Write the final `agent.audit.v1` YAML to `agent-audit.yaml` and the",
            f"plain-language `{AUDIT_SUMMARY_SCHEMA}` JSON to `{AUDIT_SUMMARY_NAME}`.",
            "Do not modify any other file and do not settle findings.",
            "",
        ]),
    )

    run(["git", "init", "-q"], cwd=workspace)
    run(
        ["git", "add", "AUDITOR.md", "AUDIT_TASK.md", "recovery-packet.md"],
        cwd=workspace,
    )
    if ll_path is not None:
        run(["git", "add", "effective-ll.md"], cwd=workspace)
    run([
        "git", "-c", "user.name=save-context-audit",
        "-c", "user.email=save-context-audit@local",
        "commit", "-q", "-m", "Prepare isolated audit input",
    ], cwd=workspace)


def parse_audit_candidates(content: str) -> dict[str, list[str]]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("YAML support is required to read audit output") from error

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_unique_mapping(
        loader: Any, node: Any, deep: bool = False
    ) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_unique_mapping,
    )
    try:
        audit = yaml.load(content, Loader=UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise RuntimeError(f"audit output is invalid YAML: {error}") from error
    if not isinstance(audit, dict):
        raise RuntimeError("audit output must be a YAML mapping")

    lanes: dict[str, list[str]] = {}
    for lane in ("execution_friction", "prompt_contract_gaps"):
        items = audit.get(lane)
        if not isinstance(items, list):
            raise RuntimeError(f"audit output lane {lane} must be a list")
        ids: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                raise RuntimeError(f"audit output lane {lane} item must be a mapping")
            audit_id = item.get("audit_id")
            if not isinstance(audit_id, str) or not audit_id or audit_id in ids:
                raise RuntimeError(f"duplicate or empty audit_id in {lane}")
            ids.append(audit_id)
        lanes[lane] = ids
    return lanes


def read_audit_output(output_path: Path) -> tuple[str, dict[str, list[str]]]:
    if not output_path.is_file():
        raise RuntimeError(f"audit output not found: {output_path}")
    content = output_path.read_text(encoding="utf-8")
    if re.search(r"(?m)^schema:\s*agent\.audit\.v1\s*$", content) is None:
        raise RuntimeError(f"audit output has invalid schema: {output_path}")
    return content, parse_audit_candidates(content)


def read_audit_summary(
    summary_path: Path,
    thread_id: str,
    candidates: dict[str, list[str]],
) -> dict[str, Any]:
    if not summary_path.is_file():
        raise RuntimeError(f"audit summary not found: {summary_path}")
    summary = parse_json_object(
        summary_path.read_text(encoding="utf-8"), "audit summary"
    )
    if summary.get("schema") != AUDIT_SUMMARY_SCHEMA:
        raise RuntimeError(f"audit summary has invalid schema: {summary_path}")
    if summary.get("thread_id") != thread_id:
        raise RuntimeError(f"audit summary thread_id does not match receipt: {summary_path}")
    for field in ("object", "finding", "recommendation"):
        if not isinstance(summary.get(field), str) or not summary[field]:
            raise RuntimeError(f"audit summary is missing {field}: {summary_path}")
    evidence = summary.get("evidence")
    if not isinstance(evidence, list) or len(evidence) > 3 or any(
        not isinstance(item, str) or not item for item in evidence
    ):
        raise RuntimeError(f"audit summary evidence is invalid: {summary_path}")
    expected_ids = [
        candidate_id
        for lane in ("execution_friction", "prompt_contract_gaps")
        for candidate_id in candidates[lane]
    ]
    return {**summary, "candidate_ids": expected_ids}


def settlement_path_for(receipt_path: Path) -> Path:
    return receipt_path.parent / SETTLEMENT_NAME


def inspection_path_for(receipt_path: Path) -> Path:
    return receipt_path.parent / INSPECTION_NAME


def project_cwd_from_receipt(receipt_path: Path, receipt: dict[str, Any]) -> str:
    project_cwd = receipt.get("project_cwd")
    if isinstance(project_cwd, str) and project_cwd:
        return project_cwd
    task_path = receipt_path.parent / "workspace" / "AUDIT_TASK.md"
    if not task_path.is_file():
        raise RuntimeError("receipt is missing project_cwd and AUDIT_TASK.md")
    match = re.search(
        r"(?m)^- project_cwd: `([^`]+)`$",
        task_path.read_text(encoding="utf-8"),
    )
    if match is None:
        raise RuntimeError("AUDIT_TASK.md is missing project_cwd")
    return match.group(1)


def canonical_optional_path(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise RuntimeError("receipt source path is invalid")
    return str(Path(value).expanduser().resolve())


def validate_receipt_layout(
    receipt_path: Path,
    receipt: dict[str, Any],
) -> tuple[Path, Path]:
    workspace_value = receipt.get("workspace")
    output_value = receipt.get("output_path")
    if not isinstance(workspace_value, str) or not isinstance(output_value, str):
        raise RuntimeError("receipt is missing workspace or output_path")
    expected_workspace = (receipt_path.parent / "workspace").resolve()
    workspace = Path(workspace_value).expanduser().resolve()
    output_path = Path(output_value).expanduser().resolve()
    if workspace != expected_workspace:
        raise RuntimeError(f"receipt workspace escapes audit directory: {workspace}")
    if output_path != workspace / "agent-audit.yaml":
        raise RuntimeError(f"receipt output_path is outside the fixed workspace output: {output_path}")
    return workspace, output_path


def read_settlement(path: Path, audit_id: str) -> dict[str, Any]:
    settlement = parse_json_object(path.read_text(encoding="utf-8"), "settlement")
    if settlement.get("schema") != SETTLEMENT_SCHEMA:
        raise RuntimeError(f"settlement has invalid schema: {path}")
    if settlement.get("audit_id") != audit_id:
        raise RuntimeError(f"settlement audit_id does not match receipt: {path}")
    status_value = settlement.get("status")
    items = settlement.get("items")
    counts = settlement.get("candidate_counts")
    if not isinstance(items, list) or not isinstance(counts, dict):
        raise RuntimeError(f"settlement is missing items or candidate_counts: {path}")
    if status_value == "discarded":
        if items or settlement.get("terminal_status") not in TERMINAL_FAILURES:
            raise RuntimeError(f"discarded settlement has invalid terminal evidence: {path}")
        if not isinstance(settlement.get("reason"), str) or not settlement["reason"]:
            raise RuntimeError(f"discarded settlement is missing reason: {path}")
        return settlement
    if status_value == "superseded":
        if items or counts:
            raise RuntimeError(f"superseded settlement has candidates: {path}")
        if not all(
            isinstance(settlement.get(field), str) and settlement[field]
            for field in (
                "successor_audit_id", "successor_run_id", "successor_receipt",
                "reason",
            )
        ):
            raise RuntimeError(f"superseded settlement is incomplete: {path}")
        return settlement
    if status_value != "settled":
        raise RuntimeError(f"settlement has invalid status: {path}")
    expected_lanes = {"execution_friction", "prompt_contract_gaps"}
    if set(counts) != expected_lanes or any(
        not isinstance(value, int) or value < 0 for value in counts.values()
    ):
        raise RuntimeError(f"settled candidate_counts are invalid: {path}")
    seen: set[tuple[str, str]] = set()
    actual_counts = {lane: 0 for lane in expected_lanes}
    requires_occurrence = False
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError(f"settlement item is not an object: {path}")
        lane = item.get("lane")
        candidate_id = item.get("audit_id")
        disposition = item.get("disposition")
        key = (lane, candidate_id)
        if lane not in expected_lanes or not isinstance(candidate_id, str) or key in seen:
            raise RuntimeError(f"settlement item identity is invalid: {path}")
        if disposition not in DISPOSITIONS:
            raise RuntimeError(f"settlement item disposition is invalid: {path}")
        if not isinstance(item.get("destination"), str) or not item["destination"]:
            raise RuntimeError(f"settlement item destination is missing: {path}")
        if not isinstance(item.get("reason"), str) or not item["reason"]:
            raise RuntimeError(f"settlement item reason is missing: {path}")
        if disposition in {"promoted", "resolved", "deferred"} and (
            not isinstance(item.get("durable_ref"), str) or not item["durable_ref"]
        ):
            raise RuntimeError(f"settlement item durable_ref is missing: {path}")
        if disposition == "promoted" and item.get("destination") == "global_friction":
            signature = item.get("signature")
            if signature is not None and (
                not isinstance(signature, str) or not signature
            ):
                raise RuntimeError(
                    f"settlement item signature is invalid: {path}"
                )
            if isinstance(signature, str):
                requires_occurrence = True
        seen.add(key)
        actual_counts[lane] += 1
    if actual_counts != counts:
        raise RuntimeError(f"settlement candidate_counts do not match items: {path}")
    occurrence = settlement.get("occurrence")
    if occurrence is not None:
        if not isinstance(occurrence, dict) or not all(
            isinstance(occurrence.get(field), str) and occurrence[field]
            for field in ("kind", "key", "thread_id", "project_cwd")
        ):
            raise RuntimeError(f"settlement occurrence identity is invalid: {path}")
        if occurrence["kind"] != "codex_thread_project":
            raise RuntimeError(f"settlement occurrence kind is invalid: {path}")
        expected_occurrence = codex_thread_project_occurrence(
            occurrence["thread_id"], occurrence["project_cwd"]
        )
        if any(
            occurrence[field] != expected_occurrence[field]
            for field in ("key", "thread_id", "project_cwd")
        ):
            raise RuntimeError(f"settlement occurrence key is invalid: {path}")
    if requires_occurrence and occurrence is None:
        raise RuntimeError(f"settlement occurrence identity is missing: {path}")
    return settlement


def read_inspection(path: Path, run_id: str) -> dict[str, Any]:
    inspection = parse_json_object(path.read_text(encoding="utf-8"), "inspection")
    if inspection.get("schema") != INSPECTION_SCHEMA:
        raise RuntimeError(f"inspection has invalid schema: {path}")
    if inspection.get("run_id") != run_id:
        raise RuntimeError(f"inspection run_id does not match receipt: {path}")
    return inspection


def candidate_counts(candidates: dict[str, list[str]]) -> dict[str, int]:
    return {lane: len(ids) for lane, ids in candidates.items()}


def codex_thread_project_occurrence(thread_id: str,
                                    project_cwd: str) -> dict[str, str]:
    canonical_cwd = str(Path(project_cwd).expanduser().resolve())
    identity = json.dumps(
        {"project_cwd": canonical_cwd, "thread_id": thread_id},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "kind": "codex_thread_project",
        "key": "codex-thread-project:" + hashlib.sha256(identity.encode()).hexdigest(),
        "thread_id": thread_id,
        "project_cwd": canonical_cwd,
    }


def occurrence_from_receipt(
    receipt_path: Path,
    receipt: dict[str, Any],
) -> dict[str, str]:
    thread_id = receipt.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise RuntimeError("receipt is missing thread_id for promoted friction")
    return codex_thread_project_occurrence(
        thread_id,
        project_cwd_from_receipt(receipt_path, receipt),
    )


def settlement_result(settlement: dict[str, Any], path: Path) -> dict[str, Any]:
    return {**settlement, "settlement_path": str(path), "cleanup_ready": True}


def local_receipt_state(receipt_path: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    _, output_path = validate_receipt_layout(receipt_path, receipt)
    audit_id = receipt.get("audit_id")
    run_id = receipt.get("run_id")
    if not isinstance(audit_id, str) or not isinstance(run_id, str):
        raise RuntimeError("receipt is missing audit_id or run_id")
    settlement_path = settlement_path_for(receipt_path)
    if settlement_path.is_file():
        settlement = read_settlement(settlement_path, audit_id)
        settlement_status = settlement.get("status")
        if settlement_status not in {"settled", "discarded", "superseded"}:
            raise RuntimeError(f"settlement has invalid status: {settlement_path}")
        return {
            **receipt,
            "status": settlement_status,
            "settlement_path": str(settlement_path),
            "candidate_counts": settlement.get("candidate_counts", {}),
            **{
                key: settlement[key]
                for key in (
                    "successor_audit_id",
                    "successor_run_id",
                    "successor_receipt",
                    "reason",
                )
                if key in settlement
            },
            "cleanup_ready": True,
        }
    if output_path.is_file():
        _, candidates = read_audit_output(output_path)
        summary = None
        summary_value = receipt.get("summary_path")
        if summary_value is not None:
            if not isinstance(summary_value, str) or not summary_value:
                raise RuntimeError("receipt summary_path is invalid")
            thread_id = receipt.get("thread_id")
            if not isinstance(thread_id, str) or not thread_id:
                raise RuntimeError("receipt thread_id is invalid")
            expected_summary_path = receipt_path.parent / "workspace" / AUDIT_SUMMARY_NAME
            summary_path = Path(summary_value).expanduser().resolve()
            if summary_path != expected_summary_path.resolve():
                raise RuntimeError("receipt summary_path is outside the audit workspace")
            summary = read_audit_summary(summary_path, thread_id, candidates)
        return {
            **receipt,
            "status": "ready",
            "candidate_counts": candidate_counts(candidates),
            **({"audit_summary": summary} if summary is not None else {}),
            "needs_settlement": True,
            "cleanup_ready": False,
        }
    inspection_path = inspection_path_for(receipt_path)
    if inspection_path.is_file():
        inspection = read_inspection(inspection_path, run_id)
        return {
            **receipt,
            **inspection,
            "output_path": str(output_path),
            "output_exists": False,
            "recoverable": False,
            "needs_discard": True,
            "cleanup_ready": False,
        }
    return receipt


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    frozen_packet = getattr(args, "recovery_packet", None)
    if frozen_packet is None:
        rollout = save_context_recover.locate_rollout(
            Path(args.codex_home).expanduser(), args.rollout, args.thread_id
        ).resolve()
    else:
        if not isinstance(frozen_packet, str) or not frozen_packet:
            raise RuntimeError("frozen recovery packet is invalid")
        if not isinstance(args.rollout, str) or not args.rollout:
            raise RuntimeError("frozen recovery packet is missing its rollout anchor")
        rollout = Path(args.rollout).expanduser().resolve()
    ll_path = Path(args.ll).expanduser().resolve() if args.ll else None
    if ll_path is not None and not ll_path.is_file():
        raise RuntimeError(f"LL contract not found: {ll_path}")

    if frozen_packet is None:
        packet_args = argparse.Namespace(
            max_messages=args.max_messages,
            max_tool_calls=args.max_tool_calls,
            max_paths=args.max_paths,
            max_context_blocks=args.max_context_blocks,
            max_text_chars=args.max_text_chars,
            max_context_chars=args.max_context_chars,
        )
        packet = save_context_recover.build_packet(rollout, packet_args)
    else:
        packet = frozen_packet
    thread_id = packet_thread_id(packet, args.thread_id or rollout.stem)
    project_cwd = Path(args.cwd).expanduser().resolve()
    audit_id = audit_identity(packet, args.route, ll_path)
    audit_dir = Path(args.audit_root).expanduser().resolve() / audit_id
    workspace = audit_dir / "workspace"
    receipt_path = audit_dir / "receipt.json"
    output_path = workspace / "agent-audit.yaml"
    summary_path = workspace / AUDIT_SUMMARY_NAME

    if receipt_path.is_file():
        receipt = parse_json_object(receipt_path.read_text(encoding="utf-8"), "receipt")
        return local_receipt_state(receipt_path, receipt)
    if audit_dir.exists():
        raise RuntimeError(f"incomplete audit directory already exists: {audit_dir}")

    audit_dir.mkdir(parents=True)
    try:
        initialize_workspace(
            workspace,
            packet,
            project_cwd,
            args.route,
            thread_id,
            ll_path,
        )
        run_file = audit_dir / "run.json"
        request_id = f"save-context-audit-{audit_id}"
        run_request = {
            "schemaVersion": "RunIntent@1",
            "requestId": request_id,
            "objective": (
                "Delegate the isolated save-context audit in AUDIT_TASK.md to the "
                "admitted audit participant. The worker must not delegate. Complete "
                "only after agent-audit.yaml and audit-summary.json satisfy the task contract."
            ),
            "acceptance": [
                "agent-audit.yaml exists in the admitted workspace",
                "agent-audit.yaml uses the exact agent.audit.v1 schema",
                "audit-summary.json exists and uses save-context.audit-summary.v1",
                "audit-summary.json satisfies the plain-language summary contract",
                "The terminal result cites both output artifacts",
            ],
            "contextRefs": [
                (workspace / "AUDIT_TASK.md").as_uri(),
                (workspace / "recovery-packet.md").as_uri(),
            ],
            "workspaceRef": workspace.as_uri(),
            "desiredEffect": "change",
            "terminalEvidence": [output_path.as_uri(), summary_path.as_uri()],
        }
        write_text(
            run_file,
            json.dumps(run_request, ensure_ascii=False, indent=2) + "\n",
        )
        started = parse_json_object(
            run([
                str(Path(args.rs_command).expanduser()),
                "run", "start", str(run_file),
            ]),
            "rs run start",
        )
        run_value = started.get("run")
        run_id = (
            run_value.get("runId")
            if isinstance(run_value, dict)
            else started.get("runId")
        )
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("rs run start did not return runId")
    except (OSError, RuntimeError):
        shutil.rmtree(audit_dir)
        raise

    receipt = {
        "schema": "save-context.audit-dispatch.v1",
        "audit_id": audit_id,
        "status": "pending",
        "dispatch_contract": DISPATCH_CONTRACT_REVISION,
        "run_id": run_id,
        "participant_policy": "runtime-selected",
        "thread_id": thread_id,
        "route": args.route,
        "project_cwd": str(project_cwd),
        "rollout": str(rollout),
        "ll_path": str(ll_path) if ll_path else None,
        "workspace": str(workspace),
        "output_path": str(output_path),
        "summary_path": str(summary_path),
        "receipt_path": str(receipt_path),
    }
    write_text(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def redispatch(args: argparse.Namespace) -> dict[str, Any]:
    source_receipt_path = Path(args.receipt).expanduser().resolve()
    source_receipt = parse_json_object(
        source_receipt_path.read_text(encoding="utf-8"),
        "source receipt",
    )
    source_state = local_receipt_state(source_receipt_path, source_receipt)
    if source_state.get("status") in {"ready", "settled", "discarded", "superseded"}:
        raise RuntimeError(
            f"source receipt cannot be redispatched from status {source_state.get('status')}"
        )
    rollout = source_receipt.get("rollout")
    route = source_receipt.get("route")
    if not all(isinstance(value, str) and value for value in (rollout, route)):
        raise RuntimeError("source receipt is missing rollout or route")
    ll_value = source_receipt.get("ll_path")
    if ll_value is not None and not isinstance(ll_value, str):
        raise RuntimeError("source receipt ll_path is invalid")
    recovery_packet_path = source_receipt_path.parent / "workspace" / "recovery-packet.md"
    if not recovery_packet_path.is_file():
        raise RuntimeError("source receipt is missing its frozen recovery packet")
    dispatch_args = argparse.Namespace(
        rollout=rollout,
        thread_id=None,
        cwd=project_cwd_from_receipt(source_receipt_path, source_receipt),
        route=route,
        ll=ll_value,
        rs_command=args.rs_command,
        audit_root=str(source_receipt_path.parent.parent),
        codex_home=args.codex_home,
        max_messages=args.max_messages,
        max_tool_calls=args.max_tool_calls,
        max_paths=args.max_paths,
        max_context_blocks=args.max_context_blocks,
        max_text_chars=args.max_text_chars,
        max_context_chars=args.max_context_chars,
        recovery_packet=recovery_packet_path.read_text(encoding="utf-8"),
    )
    successor = dispatch(dispatch_args)
    source_audit_id = source_receipt.get("audit_id")
    successor_audit_id = successor.get("audit_id")
    if source_audit_id == successor_audit_id:
        raise RuntimeError("dispatch contract revision did not produce a new audit identity")
    successor_receipt_path = Path(successor["receipt_path"]).resolve()
    persisted = parse_json_object(
        successor_receipt_path.read_text(encoding="utf-8"),
        "successor receipt",
    )
    expected_supersedes = {
        "audit_id": source_audit_id,
        "receipt": str(source_receipt_path),
    }
    existing_supersedes = persisted.get("supersedes")
    if existing_supersedes not in (None, expected_supersedes):
        raise RuntimeError("successor receipt already supersedes a different audit")
    persisted["supersedes"] = expected_supersedes
    write_text_atomic(
        successor_receipt_path,
        json.dumps(persisted, ensure_ascii=False, indent=2) + "\n",
    )
    return local_receipt_state(successor_receipt_path, persisted)


def status(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = parse_json_object(
        receipt_path.read_text(encoding="utf-8"),
        "receipt",
    )
    run_id = receipt.get("run_id")
    output_value = receipt.get("output_path")
    if not isinstance(run_id, str) or not isinstance(output_value, str):
        raise RuntimeError("receipt is missing run_id or output_path")
    local_state = local_receipt_state(receipt_path, receipt)
    if local_state.get("status") in {
        "ready", "settled", "discarded", "superseded", "failed", "cancelled", "aborted",
    }:
        return {
            key: local_state[key]
            for key in (
                "status", "run_id", "output_path", "candidate_counts",
                "audit_summary",
                "needs_settlement", "needs_discard", "settlement_path",
                "inspection_path", "recoverable", "output_exists",
                "terminal_summary", "cleanup_ready",
                "successor_audit_id", "successor_run_id", "successor_receipt",
                "reason",
            )
            if key in local_state
        }
    output_path = Path(output_value)

    inspected = parse_json_object(
        run([
            str(Path(args.rs_command).expanduser()),
            "run", "inspect", run_id,
        ]),
        "rs run inspect",
    )
    run_summary = inspected.get("summary")
    if not isinstance(run_summary, dict):
        raise RuntimeError("rs run inspect is missing summary")
    run_status = run_summary.get("status")
    summary = run_summary.get("terminalSummary")
    normalized_status = run_status if isinstance(run_status, str) else "unknown"
    terminal_failed = normalized_status in TERMINAL_FAILURES
    result = {
        "status": normalized_status,
        "run_id": run_id,
        "output_path": str(output_path),
        "output_exists": False,
        "recoverable": not terminal_failed,
        "needs_discard": terminal_failed,
        "cleanup_ready": False,
        **({"terminal_summary": summary[:500]} if isinstance(summary, str) else {}),
    }
    if terminal_failed:
        inspection_path = inspection_path_for(receipt_path)
        inspection = {
            "schema": INSPECTION_SCHEMA,
            "run_id": run_id,
            "status": normalized_status,
            "inspected_at": datetime.now(timezone.utc).isoformat(),
            **({"terminal_summary": summary[:500]} if isinstance(summary, str) else {}),
        }
        write_text(
            inspection_path,
            json.dumps(inspection, ensure_ascii=False, indent=2) + "\n",
        )
        result["inspection_path"] = str(inspection_path)
    return result


def settle(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = parse_json_object(
        receipt_path.read_text(encoding="utf-8"),
        "receipt",
    )
    _, output_path = validate_receipt_layout(receipt_path, receipt)
    audit_id = receipt.get("audit_id")
    if not isinstance(audit_id, str):
        raise RuntimeError("receipt is missing audit_id")
    _, candidates = read_audit_output(output_path)
    settlement_path = settlement_path_for(receipt_path)
    if settlement_path.is_file():
        return settlement_result(read_settlement(settlement_path, audit_id), settlement_path)

    proposed = parse_json_object(
        Path(args.input).expanduser().read_text(encoding="utf-8"),
        "settlement input",
    )
    if proposed.get("schema") != SETTLEMENT_SCHEMA:
        raise RuntimeError(f"settlement input schema must be {SETTLEMENT_SCHEMA}")
    items = proposed.get("items")
    if not isinstance(items, list):
        raise RuntimeError("settlement input items must be a list")

    expected = {(lane, audit_id) for lane, ids in candidates.items() for audit_id in ids}
    actual: set[tuple[str, str]] = set()
    normalized_items: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("settlement item must be an object")
        lane = item.get("lane")
        candidate_id = item.get("audit_id")
        disposition = item.get("disposition")
        destination = item.get("destination")
        reason = item.get("reason")
        durable_ref = item.get("durable_ref")
        signature = item.get("signature")
        key = (lane, candidate_id)
        if key not in expected or key in actual:
            raise RuntimeError(f"unknown or duplicate settlement candidate: {key}")
        if disposition not in DISPOSITIONS:
            raise RuntimeError(f"invalid disposition for {key}: {disposition}")
        if not isinstance(destination, str) or not destination:
            raise RuntimeError(f"destination is required for {key}")
        if not isinstance(reason, str) or not reason:
            raise RuntimeError(f"reason is required for {key}")
        if disposition in {"promoted", "resolved", "deferred"} and (
            not isinstance(durable_ref, str) or not durable_ref
        ):
            raise RuntimeError(f"durable_ref is required for {key} ({disposition})")
        if disposition == "promoted" and destination == "global_friction" and (
            not isinstance(signature, str) or not signature
        ):
            raise RuntimeError(
                f"signature is required for {key} (promoted global_friction)"
            )
        normalized = {
            "lane": lane,
            "audit_id": candidate_id,
            "disposition": disposition,
            "destination": destination,
            "reason": reason,
        }
        if isinstance(durable_ref, str) and durable_ref:
            normalized["durable_ref"] = durable_ref
        if isinstance(signature, str) and signature:
            normalized["signature"] = signature
        normalized_items.append(normalized)
        actual.add(key)
    missing = expected - actual
    if missing:
        raise RuntimeError(f"settlement is missing candidates: {sorted(missing)}")

    promoted_items = [
        item for item in normalized_items
        if item["disposition"] == "promoted"
        and item["destination"] == "global_friction"
    ]
    occurrence = (
        occurrence_from_receipt(receipt_path, receipt) if promoted_items else None
    )
    settlement = {
        "schema": SETTLEMENT_SCHEMA,
        "audit_id": audit_id,
        "status": "settled",
        "settled_at": datetime.now(timezone.utc).isoformat(),
        "candidate_counts": candidate_counts(candidates),
        "items": normalized_items,
        **({"occurrence": occurrence} if occurrence is not None else {}),
    }
    write_text(
        settlement_path,
        json.dumps(settlement, ensure_ascii=False, indent=2) + "\n",
    )
    return settlement_result(settlement, settlement_path)


def settlement_template(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = parse_json_object(
        receipt_path.read_text(encoding="utf-8"),
        "receipt",
    )
    _, output_path = validate_receipt_layout(receipt_path, receipt)
    _, candidates = read_audit_output(output_path)
    return {
        "schema": SETTLEMENT_SCHEMA,
        "items": [
            {
                "lane": lane,
                "audit_id": audit_id,
                "disposition": "",
                "destination": "",
                "reason": "",
                "durable_ref": "",
                "signature": "",
            }
            for lane in ("execution_friction", "prompt_contract_gaps")
            for audit_id in candidates[lane]
        ],
    }


def discard(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = parse_json_object(
        receipt_path.read_text(encoding="utf-8"),
        "receipt",
    )
    _, output_path = validate_receipt_layout(receipt_path, receipt)
    audit_id = receipt.get("audit_id")
    run_id = receipt.get("run_id")
    if not all(isinstance(value, str) for value in (audit_id, run_id)):
        raise RuntimeError("receipt is missing audit_id or run_id")
    if output_path.is_file():
        raise RuntimeError("cannot discard an audit with a valid output; settle it instead")
    settlement_path = settlement_path_for(receipt_path)
    if settlement_path.is_file():
        return settlement_result(read_settlement(settlement_path, audit_id), settlement_path)
    inspection_path = inspection_path_for(receipt_path)
    if not inspection_path.is_file():
        raise RuntimeError("terminal inspection is required before discard")
    inspection = read_inspection(inspection_path, run_id)
    terminal_status = inspection.get("status")
    if terminal_status not in TERMINAL_FAILURES:
        raise RuntimeError(f"inspection is not terminal failed: {terminal_status}")
    settlement = {
        "schema": SETTLEMENT_SCHEMA,
        "audit_id": audit_id,
        "run_id": run_id,
        "status": "discarded",
        "terminal_status": terminal_status,
        "settled_at": datetime.now(timezone.utc).isoformat(),
        "candidate_counts": {},
        "items": [],
        "reason": args.reason,
    }
    write_text(
        settlement_path,
        json.dumps(settlement, ensure_ascii=False, indent=2) + "\n",
    )
    return settlement_result(settlement, settlement_path)


def supersede(args: argparse.Namespace) -> dict[str, Any]:
    source_receipt_path = Path(args.receipt).expanduser().resolve()
    successor_receipt_path = Path(args.successor_receipt).expanduser().resolve()
    source = parse_json_object(
        source_receipt_path.read_text(encoding="utf-8"), "source receipt"
    )
    successor = parse_json_object(
        successor_receipt_path.read_text(encoding="utf-8"), "successor receipt"
    )
    _, source_output = validate_receipt_layout(source_receipt_path, source)
    if source_output.is_file():
        raise RuntimeError("source receipt has output; settle it instead of superseding")
    source_audit_id = source.get("audit_id")
    successor_audit_id = successor.get("audit_id")
    successor_run_id = successor.get("run_id")
    if not all(
        isinstance(value, str) and value
        for value in (source_audit_id, successor_audit_id, successor_run_id)
    ):
        raise RuntimeError("source or successor receipt is missing identity")
    expected_supersedes = {
        "audit_id": source_audit_id,
        "receipt": str(source_receipt_path),
    }
    if successor.get("supersedes") != expected_supersedes:
        raise RuntimeError("successor receipt is not bound to the source receipt")
    for field in ("thread_id", "route"):
        if source.get(field) != successor.get(field):
            raise RuntimeError(f"successor receipt source mismatch: {field}")
    for field in ("rollout", "ll_path"):
        if canonical_optional_path(source.get(field)) != canonical_optional_path(
            successor.get(field)
        ):
            raise RuntimeError(f"successor receipt source mismatch: {field}")
    if str(Path(project_cwd_from_receipt(source_receipt_path, source)).resolve()) != str(
        Path(project_cwd_from_receipt(successor_receipt_path, successor)).resolve()
    ):
        raise RuntimeError("successor receipt source mismatch: project_cwd")
    successor_state = local_receipt_state(successor_receipt_path, successor)
    if successor_state.get("status") not in {"ready", "settled"}:
        raise RuntimeError("successor receipt must be ready or settled")
    settlement_path = settlement_path_for(source_receipt_path)
    if settlement_path.is_file():
        return settlement_result(
            read_settlement(settlement_path, source_audit_id), settlement_path
        )
    settlement = {
        "schema": SETTLEMENT_SCHEMA,
        "audit_id": source_audit_id,
        "run_id": source.get("run_id"),
        "status": "superseded",
        "settled_at": datetime.now(timezone.utc).isoformat(),
        "candidate_counts": {},
        "items": [],
        "successor_audit_id": successor_audit_id,
        "successor_run_id": successor_run_id,
        "successor_receipt": str(successor_receipt_path),
        "reason": args.reason,
    }
    write_text_atomic(
        settlement_path,
        json.dumps(settlement, ensure_ascii=False, indent=2) + "\n",
    )
    return settlement_result(settlement, settlement_path)


def prune(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = parse_json_object(
        receipt_path.read_text(encoding="utf-8"),
        "receipt",
    )
    workspace, _ = validate_receipt_layout(receipt_path, receipt)
    audit_id = receipt.get("audit_id")
    if not isinstance(audit_id, str):
        raise RuntimeError("receipt is missing audit_id")
    settlement_path = settlement_path_for(receipt_path)
    settlement = read_settlement(settlement_path, audit_id)
    if settlement.get("status") not in {"settled", "discarded", "superseded"}:
        raise RuntimeError("audit is not cleanup-ready")
    candidates = [workspace, receipt_path.parent / "run.json"]
    existing = [path for path in candidates if path.exists()]
    bundle, digest_path = archive_paths(
        receipt_path, settlement, audit_id, args.archive_root
    )
    result = {
        "status": "cleanup-ready",
        "dry_run": not args.yes,
        "paths": [str(path) for path in existing],
        "bytes": sum(path_size(path) for path in existing),
        "archive_path": str(bundle),
        "archive_digest_path": str(digest_path),
        "archive_exists": bundle.is_file(),
        "retained": [
            str(path)
            for path in (receipt_path, settlement_path, inspection_path_for(receipt_path))
            if path.exists()
        ],
    }
    if not args.yes:
        return result
    bundle, digest_path, digest = ensure_bundle(
        receipt_path,
        receipt,
        settlement,
        workspace,
        args.archive_root,
        args.zstd_command,
    )
    for path in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    return {
        **result,
        "status": "pruned",
        "dry_run": False,
        "archive_path": str(bundle),
        "archive_digest_path": str(digest_path),
        "archive_sha256": digest,
        "archive_exists": True,
    }


def inventory(args: argparse.Namespace) -> dict[str, Any]:
    audit_root = Path(args.audit_root).expanduser().resolve()
    run_archives = archived_runs(Path(args.runtime_db).expanduser().resolve())
    audits: list[dict[str, Any]] = []
    children = audit_root.iterdir() if audit_root.is_dir() else []
    for audit_dir in sorted(children):
        if (
            not audit_dir.is_dir()
            or audit_dir.is_symlink()
            or audit_dir.name == ARCHIVE_DIRECTORY
        ):
            continue
        reasons: list[str] = []
        receipt_path = audit_dir / "receipt.json"
        run_id: str | None = None
        settlement_status: str | None = None
        cleanup_paths: list[str] = []
        if not receipt_path.is_file():
            reasons.append("missing_receipt")
        else:
            try:
                receipt = parse_json_object(
                    receipt_path.read_text(encoding="utf-8"), "receipt"
                )
                workspace, _ = validate_receipt_layout(receipt_path, receipt)
                run_value = receipt.get("run_id")
                if isinstance(run_value, str):
                    run_id = run_value
                else:
                    reasons.append("missing_run_id")
                settlement_path = settlement_path_for(receipt_path)
                audit_id = receipt.get("audit_id")
                if settlement_path.is_file() and isinstance(audit_id, str):
                    settlement = read_settlement(settlement_path, audit_id)
                    settlement_status = settlement["status"]
                else:
                    reasons.append("not_settled_or_discarded")
                cleanup_paths = [
                    str(path)
                    for path in (workspace, audit_dir / "run.json")
                    if path.exists()
                ]
            except (OSError, RuntimeError) as error:
                reasons.append(f"invalid_audit:{error}")
        run_archive_status = (
            "archived"
            if run_id is not None and run_archives.get(run_id) is True
            else "current"
            if run_id is not None and run_archives.get(run_id) is False
            else "not_found"
        )
        audits.append({
            "audit_id": audit_dir.name,
            "path": str(audit_dir),
            "bytes": path_size(audit_dir),
            "run_id": run_id,
            "run_archive_status": run_archive_status,
            "settlement_status": settlement_status,
            "eligible": not reasons,
            "exclusion_reasons": reasons,
            "cleanup_paths": cleanup_paths,
        })
    return {
        "status": "inventory",
        "dry_run": True,
        "audit_root": str(audit_root),
        "runtime_db": str(Path(args.runtime_db).expanduser().resolve()),
        "count": len(audits),
        "eligible_count": sum(item["eligible"] for item in audits),
        "bytes": sum(item["bytes"] for item in audits),
        "audits": audits,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)

    dispatch_parser = commands.add_parser("dispatch")
    source = dispatch_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--rollout")
    source.add_argument("--thread-id")
    dispatch_parser.add_argument("--cwd", required=True)
    dispatch_parser.add_argument("--route", required=True)
    dispatch_parser.add_argument("--ll")
    dispatch_parser.add_argument("--rs-command", default=str(DEFAULT_RS))
    dispatch_parser.add_argument("--audit-root", default=str(DEFAULT_AUDIT_ROOT))
    dispatch_parser.add_argument(
        "--codex-home",
        default=str(save_context_recover.default_codex_home()),
    )
    dispatch_parser.add_argument("--max-messages", type=int, default=8)
    dispatch_parser.add_argument("--max-tool-calls", type=int, default=30)
    dispatch_parser.add_argument("--max-paths", type=int, default=25)
    dispatch_parser.add_argument("--max-context-blocks", type=int, default=3)
    dispatch_parser.add_argument("--max-text-chars", type=int, default=1200)
    dispatch_parser.add_argument("--max-context-chars", type=int, default=12000)

    redispatch_parser = commands.add_parser("redispatch")
    redispatch_parser.add_argument("--receipt", required=True)
    redispatch_parser.add_argument("--rs-command", default=str(DEFAULT_RS))
    redispatch_parser.add_argument(
        "--codex-home",
        default=str(save_context_recover.default_codex_home()),
    )
    redispatch_parser.add_argument("--max-messages", type=int, default=8)
    redispatch_parser.add_argument("--max-tool-calls", type=int, default=30)
    redispatch_parser.add_argument("--max-paths", type=int, default=25)
    redispatch_parser.add_argument("--max-context-blocks", type=int, default=3)
    redispatch_parser.add_argument("--max-text-chars", type=int, default=1200)
    redispatch_parser.add_argument("--max-context-chars", type=int, default=12000)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("--receipt", required=True)
    status_parser.add_argument("--rs-command", default=str(DEFAULT_RS))

    settle_parser = commands.add_parser("settle")
    settle_parser.add_argument("--receipt", required=True)
    settlement_source = settle_parser.add_mutually_exclusive_group(required=True)
    settlement_source.add_argument("--input")
    settlement_source.add_argument("--template", action="store_true")

    discard_parser = commands.add_parser("discard")
    discard_parser.add_argument("--receipt", required=True)
    discard_parser.add_argument("--reason", required=True)

    supersede_parser = commands.add_parser("supersede")
    supersede_parser.add_argument("--receipt", required=True)
    supersede_parser.add_argument("--successor-receipt", required=True)
    supersede_parser.add_argument("--reason", required=True)

    prune_parser = commands.add_parser("prune")
    prune_parser.add_argument("--receipt", required=True)
    prune_parser.add_argument("--yes", action="store_true")
    prune_parser.add_argument("--archive-root")
    prune_parser.add_argument("--zstd-command", default="zstd")

    inventory_parser = commands.add_parser("inventory")
    inventory_parser.add_argument("--audit-root", default=str(DEFAULT_AUDIT_ROOT))
    inventory_parser.add_argument(
        "--runtime-db",
        default=str(Path.home() / ".rollerskate/runtime.db"),
    )
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        if args.command == "dispatch":
            output = dispatch(args)
        elif args.command == "redispatch":
            output = redispatch(args)
        elif args.command == "status":
            output = status(args)
        elif args.command == "settle":
            output = settlement_template(args) if args.template else settle(args)
        elif args.command == "discard":
            output = discard(args)
        elif args.command == "supersede":
            output = supersede(args)
        elif args.command == "prune":
            output = prune(args)
        else:
            output = inventory(args)
    except (OSError, RuntimeError) as error:
        print(f"save-context-audit-rs: {error}", file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
