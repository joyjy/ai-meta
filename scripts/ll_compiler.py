"""Deterministically compile a dispatch-ready final-form payload into LL."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ll_contract_file import (
    HOT_PACKET_HARD_LIMIT,
    HOT_PACKET_PROTOCOL,
    HOT_PACKET_SOFT_TARGET,
)

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CONTRACT = SCRIPT_DIR / "fixtures" / "ll-contracts" / "base_ll_contract.json"
INVENTORY_FIELDS = {
    "prior_entries",
    "behavior_rules",
    "runtime_data_sources",
    "runtime_integrations",
    "domain_roles",
    "counterexamples",
}


def text(value: Any) -> str:
    return " ".join(str(value or "").split())


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text(item) for item in value if text(item)]


def mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def compile_contract(payload: dict[str, Any], *, workitem: bool = False) -> dict[str, Any]:
    ff = payload.get("ff")
    if not isinstance(ff, dict):
        raise ValueError("ff must be an object")

    ff_bytes = json.dumps(
        ff, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    source_id = text(payload.get("id"))
    if workitem and not source_id:
        raise ValueError("id is required")
    if not source_id:
        source_id = "ff-" + hashlib.sha256(ff_bytes).hexdigest()[:12]

    goal = text(ff.get("goal"))
    acceptance = unique(string_list(ff.get("acceptance")))
    if not goal:
        raise ValueError("ff.goal is required")
    if not acceptance:
        raise ValueError("ff.acceptance requires at least one item")
    if ff.get("ready_for_dispatch") is not True:
        raise ValueError("ff.ready_for_dispatch must be true")
    if string_list(ff.get("blocking_questions")):
        raise ValueError("ff.blocking_questions must be empty")
    dispatch_target = text(ff.get("dispatch_target")) or "codex"
    allowed_dispatch_targets = {"codex", "symphony"} if workitem else {"codex"}
    if dispatch_target not in allowed_dispatch_targets:
        raise ValueError(
            "loop-ledger requires ff.dispatch_target=codex; the WorkItem "
            "compatibility entry also accepts symphony")

    source = text(payload.get("authorization_source")) or (
        "user_confirmation" if workitem else "user_request")
    if source not in {"user_request", "user_confirmation"}:
        raise ValueError(
            "authorization_source must be user_request or user_confirmation")

    contract = json.loads(BASE_CONTRACT.read_text(encoding="utf-8"))
    ll = contract["ll_contract"]
    safe_id = "".join(
        char if char.isalnum() or char in "._-" else "-" for char in source_id
    ).strip("-") or "ll"
    ll["id"] = f"{'symphony' if workitem else 'll'}-{safe_id}"
    ll["project"] = {
        "abbr": text(payload.get("project_abbr")) or (
            "symphony" if workitem else "project"),
        "root": text(payload.get("project_root")) or str(Path.cwd()),
        "gitlab_flow": text(payload.get("gitlab_flow")) or "unknown",
    }
    ll["applies_to"] = {"skill": "loop-ledger", "scope": "project"}

    scope = mapping(ff.get("scope"))
    include = unique(string_list(scope.get("include")))
    exclude = unique(string_list(scope.get("exclude")))
    if not workitem and not include:
        raise ValueError("ff.scope.include requires at least one item")
    ll["target"]["outcome"] = goal
    ll["target"]["required_artifacts"] = include or ["implementation evidence"]
    ll["target"]["out_of_scope"] = unique(
        exclude + ["remote_write_without_confirmation", "destructive_change"])

    inventory = mapping(ff.get("existing_capability_inventory"))
    normalized_inventory = {
        key: string_list(inventory.get(key))
        for key in INVENTORY_FIELDS
        if string_list(inventory.get(key))
    }
    if normalized_inventory:
        ll["target"]["existing_capability_inventory"] = normalized_inventory
    else:
        ll["target"].pop("existing_capability_inventory", None)

    continuation = mapping(ff.get("continuation"))
    continuation_conditions: list[str] = []
    if continuation:
        targets = continuation.get("supported_targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError(
                "ff.continuation.supported_targets requires at least one target")
        for target in targets:
            if not isinstance(target, dict) or any(
                    not text(target.get(key))
                    for key in ["surface", "activity", "transport"]):
                raise ValueError(
                    "each continuation target requires surface, activity, and transport")
            activity = text(target.get("activity"))
            if activity not in {"idle", "active"}:
                raise ValueError(
                    "continuation target activity must be idle or active")
            continuation_conditions.append(
                "continuation target " + text(target.get("surface")) + "/" +
                activity + " uses " + text(target.get("transport")))
        for key in [
                "admission", "queue_visibility", "completion_visibility",
                "idempotency"]:
            value = text(continuation.get(key))
            if not value:
                raise ValueError(f"ff.continuation.{key} is required")
            continuation_conditions.append(
                "continuation " + key.replace("_", " ") + ": " + value)

    verification_loop = mapping(ff.get("verification_loop"))
    stop_conditions = string_list(verification_loop.get("stop_conditions"))
    done_when = unique(acceptance + stop_conditions + continuation_conditions)
    ll["verification"]["commands"] = string_list(ff.get("checks"))
    ll["verification"]["state_checks"] = [
        "effective LL state and session metadata are consistent"
    ]
    ll["verification"]["done_when"] = done_when
    ll["verification"]["acceptance_sources"] = [
        {
            "done_when": item,
            "source_type": (
                "inferred" if item in stop_conditions else "user_feedback"),
            "evidence": (
                "authorized final-form acceptance"
                if item in acceptance
                else (
                    "final-form verification_loop.stop_conditions"
                    if item in stop_conditions
                    else "final-form continuation contract")
            ),
        }
        for item in done_when
    ]
    ll["verification"]["substitute_evidence"] = [
        "validated result evidence bound to the active hot revision"
    ]

    constraints = string_list(ff.get("constraints"))
    constraint_text = " ".join(constraints).casefold()
    if any(marker in constraint_text for marker in [
            "只读", "read-only", "read only", "no writes"]):
        ll["authorization"]["allowed_side_effects"] = ["read"]
    else:
        ll["authorization"]["allowed_side_effects"] = [
            "read", "local_edit", "light_test"]
    if constraints:
        ll["target"]["out_of_scope"].extend(
            f"constraint: {constraint}" for constraint in constraints)

    if continuation:
        contract["runtime_binding"]["continuation"] = continuation

    contract["runtime_binding"]["adapter"] = "codex_goal"
    contract["runtime_binding"]["objective"] = goal
    contract["runtime_binding"]["hot_packet"] = {
        "protocol": HOT_PACKET_PROTOCOL,
        "soft_target": HOT_PACKET_SOFT_TARGET,
        "hard_limit": HOT_PACKET_HARD_LIMIT,
    }
    contract["dispatch"] = {
        "target": "manual",
        "local_execution": True,
        "goal_authorization": {
            "source": source,
            "objective_source": "verified_contract",
        },
    }
    contract["ff_binding"] = {
        "id": source_id,
        "revision_sha256": hashlib.sha256(ff_bytes).hexdigest(),
        "acceptance_sha256": hashlib.sha256(
            json.dumps(acceptance, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    if workitem:
        contract["workitem_binding"] = {
            "id": source_id,
            "title": text(payload.get("title")),
            "root_goal_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        }
    return contract
