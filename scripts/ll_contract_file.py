"""Read legacy JSON or single-file segmented loop-ledger contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FRONT_LINE_COUNT = 8
HOT_PACKET_PROTOCOL = "ll-turn@1"
HOT_PACKET_SOFT_TARGET = 1200
HOT_PACKET_HARD_LIMIT = 1800
HOT_PACKET_LEGACY_LIMITS = {(800, 1200)}
CONTRACT_MARKER = "--- ll.contract.v0 ---"
LEDGER_MARKER = "--- ll.ledger.v1 ---"
FRONT_PREFIXES = [
    "LL: ",
    "Goal: ",
    "Scope: ",
    "Done: ",
    "Guardrails: ",
    "Ordinary: ",
    "Recovery: ",
    "Contract: ",
]


@dataclass(frozen=True)
class LLDocument:
    contract: dict[str, Any]
    front: list[str]
    events: list[dict[str, Any]]
    segmented: bool


@dataclass(frozen=True)
class LLRuntimeProjection:
    root_goal: str
    active_focus: dict[str, Any] | None
    pending_focuses: list[dict[str, Any]]
    status: str
    revision: str
    last_summary: str | None


def _merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def apply_event(contract: dict[str, Any], event: dict[str, Any]) -> None:
    event_type = event.get("type")
    if event_type == "contract_patch":
        patch = event.get("patch")
        if not isinstance(patch, dict):
            raise ValueError("contract_patch event requires object patch")
        _merge(contract, patch)
        return
    if event_type == "checkpoint":
        checkpoint_id = event.get("checkpoint")
        status = event.get("status")
        checkpoints = contract.get("ll_contract", {}).get("checkpoints", [])
        for checkpoint in checkpoints:
            if isinstance(checkpoint, dict) and checkpoint.get("id") == checkpoint_id:
                checkpoint["status"] = status
                return
        raise ValueError(f"unknown checkpoint: {checkpoint_id!r}")
    if event_type == "exit":
        exit_state = contract.setdefault("ll_contract", {}).setdefault("exit", {})
        for key in [
                "state", "next_action", "remote_write_requires_confirmation",
                "privileged_git_exit"
        ]:
            if key in event:
                exit_state[key] = event[key]
        return
    if event_type == "feedback":
        item = event.get("item")
        if not isinstance(item, dict):
            raise ValueError("feedback event requires object item")
        contract.setdefault("feedback", []).append(copy.deepcopy(item))
        return
    if event_type == "evidence":
        return
    if event_type == "root_amendment":
        goal = event.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("root_amendment event requires non-empty goal")
        normalized = " ".join(goal.split())
        contract.setdefault("ll_contract", {}).setdefault("target", {})[
            "outcome"] = normalized
        contract.setdefault("runtime_binding", {})["objective"] = normalized
        return
    if event_type in {
            "focus_added", "focus_activated", "focus_completed",
            "focus_superseded", "reply_compiled", "hot_rejected",
            "human_decision", "session_rebind"
    }:
        _validate_runtime_event(event)
        return
    raise ValueError(f"unsupported ledger event type: {event_type!r}")


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_runtime_event(event: dict[str, Any]) -> None:
    event_type = event.get("type")
    if event_type == "focus_added":
        focus = event.get("focus")
        if not isinstance(focus, dict):
            raise ValueError("focus_added event requires object focus")
        if not _non_empty_text(focus.get("id")):
            raise ValueError("focus_added focus.id is required")
        if not _non_empty_text(focus.get("goal")):
            raise ValueError("focus_added focus.goal is required")
        return
    if event_type in {"focus_activated", "focus_completed", "focus_superseded"}:
        if not _non_empty_text(event.get("focus_id")):
            raise ValueError(f"{event_type} event requires focus_id")
        return
    if event_type == "reply_compiled":
        result = event.get("result")
        if not isinstance(result, dict):
            raise ValueError("reply_compiled event requires object result")
        if result.get("status") not in {
                "continue", "completed", "blocked", "needs_human"
        }:
            raise ValueError(
                "reply_compiled result.status must be one of: continue, "
                "completed, blocked, needs_human")
        if not _non_empty_text(result.get("summary")):
            raise ValueError("reply_compiled result.summary is required")
        evidence = result.get("evidence", [])
        if not isinstance(evidence, list) or not all(
                _non_empty_text(item) for item in evidence):
            raise ValueError(
                "reply_compiled result.evidence must be a list of non-empty strings"
            )
        if result.get("status") == "completed" and not evidence:
            raise ValueError(
                "reply_compiled completed result requires evidence")
        if "blocker" not in result:
            raise ValueError("reply_compiled result.blocker is required")
        blocker = result.get("blocker")
        if blocker is not None and not isinstance(blocker, str):
            raise ValueError(
                "reply_compiled result.blocker must be a string or null")
        if result.get("status") in {"blocked", "needs_human"}:
            if not _non_empty_text(blocker):
                raise ValueError(
                    "reply_compiled blocked result requires blocker text")
        elif _non_empty_text(blocker):
            raise ValueError(
                "reply_compiled non-blocked result requires blocker=null")
        next_focus = result.get("next_focus")
        if next_focus is not None:
            if result.get("status") != "continue":
                raise ValueError(
                    "reply_compiled result.next_focus requires status=continue")
            if not isinstance(next_focus, dict):
                raise ValueError(
                    "reply_compiled result.next_focus must be an object or null")
            if not _non_empty_text(next_focus.get("id")):
                raise ValueError("reply_compiled result.next_focus.id is required")
            if not _non_empty_text(next_focus.get("goal")):
                raise ValueError("reply_compiled result.next_focus.goal is required")
            done_when = next_focus.get("done_when")
            if not isinstance(done_when, list) or not done_when or not all(
                    _non_empty_text(item) for item in done_when):
                raise ValueError(
                    "reply_compiled result.next_focus.done_when requires objective verifier text"
                )
        return
    if event_type == "hot_rejected":
        if not _non_empty_text(event.get("reason")):
            raise ValueError("hot_rejected event requires reason")
        return
    if event_type == "human_decision":
        if not _non_empty_text(event.get("decision")):
            raise ValueError("human_decision event requires decision")
        return
    if event_type == "session_rebind":
        if not _non_empty_text(event.get("from_session_id")):
            raise ValueError("session_rebind event requires from_session_id")
        if not _non_empty_text(event.get("to_session_id")):
            raise ValueError("session_rebind event requires to_session_id")
        return


def _normalized_focus(value: dict[str, Any]) -> dict[str, Any]:
    focus = copy.deepcopy(value)
    focus["id"] = str(focus["id"]).strip()
    focus["goal"] = " ".join(str(focus["goal"]).split())
    done_when = focus.get("done_when")
    focus["done_when"] = (
        [" ".join(str(item).split()) for item in done_when if str(item).strip()]
        if isinstance(done_when, list) else [])
    return focus


def runtime_projection(document: LLDocument) -> LLRuntimeProjection:
    contract = document.contract
    root_goal = _front_text(
        contract.get("ll_contract", {}).get("target", {}).get("outcome"))
    root_done = contract.get("ll_contract", {}).get("verification", {}).get(
        "done_when", [])
    focuses: dict[str, dict[str, Any]] = {
        "root": {
            "id": "root",
            "goal": root_goal,
            "done_when": copy.deepcopy(root_done) if isinstance(root_done, list) else [],
            "source": "root_contract",
        }
    }
    order = ["root"]
    terminal: set[str] = set()
    active_id: str | None = "root"
    status = "active"
    last_summary: str | None = None

    for event in document.events:
        event_type = event.get("type")
        if event_type == "root_amendment":
            root_goal = " ".join(str(event["goal"]).split())
            focuses["root"]["goal"] = root_goal
            terminal.discard("root")
        elif event_type == "focus_added":
            focus = _normalized_focus(event["focus"])
            focus_id = focus["id"]
            if focus_id in focuses:
                raise ValueError(f"focus already exists: {focus_id!r}")
            order.append(focus_id)
            focuses[focus_id] = focus
        elif event_type == "focus_activated":
            focus_id = str(event["focus_id"]).strip()
            if focus_id not in focuses:
                raise ValueError(f"unknown focus: {focus_id!r}")
            if focus_id in terminal:
                raise ValueError(f"terminal focus cannot be activated: {focus_id!r}")
            active_id = focus_id
            status = "active"
        elif event_type in {"focus_completed", "focus_superseded"}:
            focus_id = str(event["focus_id"]).strip()
            if focus_id not in focuses:
                raise ValueError(f"unknown focus: {focus_id!r}")
            terminal.add(focus_id)
            if active_id == focus_id:
                active_id = None
        elif event_type == "reply_compiled":
            if active_id is None and status == "active":
                active_id = next((
                    focus_id for focus_id in order if focus_id not in terminal
                ), None)
            result = event["result"]
            next_focus = result.get("next_focus")
            next_focus_id: str | None = None
            if isinstance(next_focus, dict):
                normalized = _normalized_focus(next_focus)
                focus_id = normalized["id"]
                if focus_id in focuses:
                    raise ValueError(f"focus already exists: {focus_id!r}")
                order.append(focus_id)
                focuses[focus_id] = normalized
                next_focus_id = focus_id
            last_summary = " ".join(str(result["summary"]).split())
            result_status = result["status"]
            if result_status in {"blocked", "needs_human"}:
                status = result_status
            elif result_status == "continue" and next_focus_id:
                if active_id and active_id != "root":
                    terminal.add(active_id)
                active_id = next_focus_id
            elif result_status == "completed" and active_id:
                terminal.add(active_id)
                active_id = None
        elif event_type == "hot_rejected":
            status = "hot_rejected"
            active_id = None
        elif event_type == "human_decision":
            status = "active"
        elif event_type == "session_rebind":
            status = "active"

    pending_ids = [focus_id for focus_id in order if focus_id not in terminal]
    if status == "active" and not pending_ids:
        status = "completed"
    if active_id not in pending_ids:
        active_id = pending_ids[0] if pending_ids and status == "active" else None
    pending = [focuses[focus_id] for focus_id in pending_ids if focus_id != active_id]
    revision_payload = json.dumps(
        {
            "root_goal": root_goal,
            "active_focus": active_id,
            "pending": [focus["id"] for focus in pending],
            "status": status,
            "events": len(document.events),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    revision = hashlib.sha256(revision_payload.encode("utf-8")).hexdigest()[:12]
    return LLRuntimeProjection(
        root_goal=root_goal,
        active_focus=focuses.get(active_id) if active_id else None,
        pending_focuses=pending,
        status=status,
        revision=revision,
        last_summary=last_summary,
    )


def _parse_events(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid ledger event JSON at event line {index}: {exc.msg}"
            ) from exc
        if not isinstance(event, dict):
            raise ValueError(f"ledger event line {index} must be an object")
        events.append(event)
    return events


def load_text(text: str) -> LLDocument:
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            contract = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc.msg}") from exc
        if not isinstance(contract, dict):
            raise ValueError("contract root must be a JSON object")
        return LLDocument(contract=contract, front=[], events=[], segmented=False)

    lines = text.splitlines()
    if len(lines) < FRONT_LINE_COUNT + 2:
        raise ValueError("segmented LL file is missing required blocks")
    front = lines[:FRONT_LINE_COUNT]
    for index, (line, prefix) in enumerate(zip(front, FRONT_PREFIXES), start=1):
        if not line.startswith(prefix):
            raise ValueError(f"front line {index} must start with {prefix!r}")
    if lines[FRONT_LINE_COUNT] != CONTRACT_MARKER:
        raise ValueError(
            f"line {FRONT_LINE_COUNT + 1} must be {CONTRACT_MARKER!r}")
    try:
        ledger_index = lines.index(LEDGER_MARKER, FRONT_LINE_COUNT + 1)
    except ValueError as exc:
        raise ValueError(f"segmented LL file is missing {LEDGER_MARKER!r}") from exc
    contract_text = "\n".join(lines[FRONT_LINE_COUNT + 1:ledger_index])
    try:
        contract = json.loads(contract_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid embedded contract JSON: {exc.msg}") from exc
    if not isinstance(contract, dict):
        raise ValueError("embedded contract root must be a JSON object")
    events = _parse_events(lines[ledger_index + 1:])
    effective = copy.deepcopy(contract)
    for event in events:
        apply_event(effective, event)
    return LLDocument(
        contract=effective,
        front=front,
        events=events,
        segmented=True,
    )


def load_path(path: Path) -> LLDocument:
    return load_text(path.read_text(encoding="utf-8"))


def _front_text(value: Any) -> str:
    if isinstance(value, list):
        text = "、".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = " ".join(str(value or "").split())
    return text or "无"


def _humanize_markers(values: list[str]) -> str:
    return "、".join(value.replace("_", " ") for value in values) or "none"


def hot_packet_budget_report(
        lines: list[str], *, soft_target: int = HOT_PACKET_SOFT_TARGET,
        hard_limit: int = HOT_PACKET_HARD_LIMIT) -> dict[str, Any]:
    length = len("\n".join(lines))
    fields = {
        line.split(":", 1)[0]: {
            "length": len(line),
        }
        for line in lines
    }
    return {
        "ok": length <= hard_limit,
        "within_soft_target": length <= soft_target,
        "length": length,
        "soft_target": soft_target,
        "hard_limit": hard_limit,
        "over_soft_by": max(0, length - soft_target),
        "over_hard_by": max(0, length - hard_limit),
        "fields": fields,
    }


def supports_hot_packet_policy(policy: Any) -> bool:
    if not isinstance(policy, dict):
        return False
    if policy.get("protocol") != HOT_PACKET_PROTOCOL:
        return False
    limits = (policy.get("soft_target"), policy.get("hard_limit"))
    return limits == (HOT_PACKET_SOFT_TARGET, HOT_PACKET_HARD_LIMIT) or \
        limits in HOT_PACKET_LEGACY_LIMITS


def hot_packet_limits(contract: dict[str, Any]) -> tuple[int, int]:
    policy = contract.get("runtime_binding", {}).get("hot_packet")
    if supports_hot_packet_policy(policy):
        return policy["soft_target"], policy["hard_limit"]
    return HOT_PACKET_SOFT_TARGET, HOT_PACKET_HARD_LIMIT


def uses_bounded_hot_packet(contract: dict[str, Any]) -> bool:
    policy = contract.get("runtime_binding", {}).get("hot_packet")
    return (isinstance(policy, dict) and
            policy.get("protocol") == HOT_PACKET_PROTOCOL)


def validate_hot_packet_budget(
        lines: list[str], *, enforce: bool = True,
        soft_target: int = HOT_PACKET_SOFT_TARGET,
        hard_limit: int = HOT_PACKET_HARD_LIMIT) -> dict[str, Any]:
    report = hot_packet_budget_report(
        lines, soft_target=soft_target, hard_limit=hard_limit)
    if report["ok"] or not enforce:
        return report
    lengths = ", ".join(
        f"{field}={details['length']}"
        for field, details in report["fields"].items()
    )
    raise ValueError(
        f"hot-packet preflight failed: total={report['length']}; "
        f"soft_target={soft_target}; "
        f"hard_limit={hard_limit}; fields: {lengths}; "
        "compact source fields or fixed protocol text without dropping "
        "required semantics")


def build_front(contract: dict[str, Any], path: Path) -> list[str]:
    ll_contract = contract.get("ll_contract", {})
    target = ll_contract.get("target", {})
    verification = ll_contract.get("verification", {})
    authorization = ll_contract.get("authorization", {})
    runtime = contract.get("runtime_binding", {})
    ask_before: list[str] = []
    for value in [authorization.get("ask_before"), runtime.get("call_user_when")]:
        if isinstance(value, list):
            for item in value:
                text = str(item).strip()
                if text and text not in ask_before:
                    ask_before.append(text)
    allowed = authorization.get("allowed_side_effects")
    allowed_items = ([str(item).strip() for item in allowed if str(item).strip()]
                     if isinstance(allowed, list) else [])
    required = _front_text(target.get("required_artifacts"))
    excluded = _front_text(target.get("out_of_scope"))
    lines = [
        f"LL: {_front_text(ll_contract.get('id'))} | ll.segmented.v1",
        f"Goal: {_front_text(target.get('outcome'))}",
        f"Scope: include={required}; exclude={excluded}",
        f"Done: {_front_text(verification.get('done_when'))}",
        "Guardrails: allowed without asking=" +
        _humanize_markers(allowed_items) + "; ask before=" +
        _humanize_markers(ask_before),
        "Ordinary: ll-hot-block only.",
        "Recovery: full file for resume/gates/transitions/final audit.",
        "Contract: this file; never infer newest.",
    ]
    return lines


def render_front(contract: dict[str, Any], path: Path) -> list[str]:
    lines = build_front(contract, path)
    soft_target, hard_limit = hot_packet_limits(contract)
    validate_hot_packet_budget(
        lines, enforce=uses_bounded_hot_packet(contract),
        soft_target=soft_target, hard_limit=hard_limit)
    return lines


def render_hot_block(document: LLDocument, path: Path) -> list[str]:
    projection = runtime_projection(document)
    contract = document.contract
    ll_contract = contract.get("ll_contract", {})
    target = ll_contract.get("target", {})
    authorization = ll_contract.get("authorization", {})
    runtime = contract.get("runtime_binding", {})
    focus = projection.active_focus
    focus_goal = _front_text(focus.get("goal")) if focus else "无；等待人工处理"
    focus_done = _front_text(focus.get("done_when")) if focus else "不得继续执行"
    ask_before: list[str] = []
    for value in [authorization.get("ask_before"), runtime.get("call_user_when")]:
        if isinstance(value, list):
            for item in value:
                text = str(item).strip()
                if text and text not in ask_before:
                    ask_before.append(text)
    lines = [
        f"LL: {_front_text(ll_contract.get('id'))} | status={projection.status} | hot={projection.revision}",
        f"Root: {projection.root_goal}",
        f"Focus: {focus_goal}",
        f"Local done: {focus_done}; then reconcile Root before terminal completion",
        f"Scope: include={_front_text(target.get('required_artifacts'))}; exclude={_front_text(target.get('out_of_scope'))}",
        "Guardrails: one active focus; Root is final authority; ask before=" +
        _humanize_markers(ask_before),
        f"Reply: {HOT_PACKET_PROTOCOL}; compile-reply with bound exact LL path; prose is not state.",
        "Contract: active goal binds exact path; never infer newest.",
    ]
    soft_target, hard_limit = hot_packet_limits(contract)
    validate_hot_packet_budget(
        lines, enforce=uses_bounded_hot_packet(contract),
        soft_target=soft_target, hard_limit=hard_limit)
    return lines


def render_segmented(contract: dict[str, Any], path: Path) -> str:
    front = render_front(contract, path)
    embedded = json.dumps(contract, ensure_ascii=False, indent=2)
    return "\n".join([*front, CONTRACT_MARKER, embedded, LEDGER_MARKER, ""])
