#!/usr/bin/env python3
"""Blind A/B check of rule text on frozen decision scenarios through Rollerskate DAG Runs; output is analysis data.

The contract (spec format, verdict rules, directories) is owned by docs/runbook/rule-eval.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402

SPEC_SCHEMA = "rule-eval.spec.v1"
RUN_SCHEMA = "rule-eval.run.v1"
RESULT_SCHEMA = "rule-eval.result.v1"
CLI = "rule-eval"
COMMANDS = ["start", "collect", "usage"]
ARMS = ("baseline", "candidate")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,23}$")  # no "_": it joins node ids
DONE_NODE = {"succeeded", "failed", "blocked", "cancelled", "needs_human"}
FINAL_RUN = {"succeeded", "failed", "cancelled"}
DONE_RUN = FINAL_RUN | {"needs_human"}  # needs_human stops node progress but keeps the Run open
MAX_NODES = 64
TASK = """# 任务

你在一个冻结的决策场景里，只做一次选择。

1. 读 RULE.md：当时生效的规则。
2. 读节点 objective 指定的 scenarios/<场景 id>/CONTEXT.md：当时的请求、已知事实和可选的下一步。
3. 按 RULE.md 选出当时应采取的下一步。只读，不修改文件，不调用外部系统，不读取其他场景。

交付物是单个 JSON 对象，不加其他文字：

{"scenario": "<场景 id>", "choice": "<选项字母>", "reason": "<不超过 200 字，写出 RULE.md 中的依据>"}
"""


class SpecError(ValueError):
    pass


def default_rs() -> Path:
    return Path(os.environ.get("RULE_EVAL_RS", Path.home() / "Documents/me/Projects/rollerskate/scripts/rs"))


def arm_of(spec: dict[str, Any], arm: str) -> dict[str, Any]:
    value = spec["arms"][arm]
    return {"rule": value} if isinstance(value, str) else value


def load_spec(path: Path) -> dict[str, Any]:
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SpecError(f"spec unreadable: {path}: {exc}") from exc
    base = path.parent
    if spec.get("schema") != SPEC_SCHEMA:
        raise SpecError(f"schema must be {SPEC_SCHEMA}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", str(spec.get("id", ""))):
        raise SpecError("id must be lowercase kebab-case, at most 48 characters")
    for arm in ARMS:
        if arm not in spec.get("arms", {}):
            raise SpecError(f"arms.{arm} missing")
        if not (base / arm_of(spec, arm).get("rule", "")).is_file():
            raise SpecError(f"arms.{arm}.rule is not a file under the spec directory")
    agents = spec.get("agents") or []
    if [a.get("target") is True for a in agents].count(True) != 1:
        raise SpecError("agents must contain exactly one target agent")
    if len({a.get("id") for a in agents}) != len(agents) or not all(NAME.match(str(a.get("id"))) for a in agents):
        raise SpecError("agent ids must be unique names")
    scenarios = spec.get("scenarios") or []
    for item in scenarios:
        if not NAME.match(str(item.get("id"))) or not (base / "scenarios" / item["id"] / "CONTEXT.md").is_file():
            raise SpecError(f"scenario {item.get('id')}: needs a name and scenarios/<id>/CONTEXT.md")
        if item.get("expected") not in (item.get("choices") or []):
            raise SpecError(f"scenario {item['id']}: expected must be one of choices")
    if not any(item.get("holdout") is True for item in scenarios):
        raise SpecError("at least one scenario must be a holdout")
    samples = spec.setdefault("samples", 1)
    if samples not in (1, 2, 3):
        raise SpecError("samples must be 1, 2 or 3")
    if len(scenarios) * len(agents) * samples + 1 > MAX_NODES:
        raise SpecError(f"scenarios x agents x samples + 1 exceeds {MAX_NODES} nodes")
    spec.setdefault("timeout_seconds", 3600)
    return spec


def cells(spec: dict[str, Any]) -> list[tuple[str, str, int]]:
    return [(s["id"], a["id"], k) for s in spec["scenarios"] for a in spec["agents"]
            for k in range(1, spec["samples"] + 1)]


def node_id(scenario: str, agent: str, sample: int) -> str:
    return f"{scenario}_{agent}_{sample}"


def selection(spec: dict[str, Any], arm: str, agent: dict[str, Any]) -> dict[str, str]:
    chosen = {key: agent[key] for key in ("model", "effort") if agent.get(key)}
    if agent.get("target"):
        chosen.update({key: value for key, value in arm_of(spec, arm).items() if key in ("model", "effort")})
    return chosen


def build_workspace(root: Path, base: Path, spec: dict[str, Any], arm: str) -> Path:
    """One Git workspace per arm, so a node can only see its own rule text and no expected answers."""
    root.mkdir(parents=True)
    (root / "TASK.md").write_text(TASK, encoding="utf-8")
    shutil.copyfile(base / arm_of(spec, arm)["rule"], root / "RULE.md")
    for item in spec["scenarios"]:
        target = root / "scenarios" / item["id"]
        target.mkdir(parents=True)
        shutil.copyfile(base / "scenarios" / item["id"] / "CONTEXT.md", target / "CONTEXT.md")
    git = ["git", "-C", str(root), "-c", "user.name=rule-eval", "-c", "user.email=rule-eval@localhost"]
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "frozen scenarios"]):
        subprocess.run(git + command, check=True, capture_output=True)
    return root


def build_intent(spec: dict[str, Any], arm: str, workspace: Path, request_id: str) -> dict[str, Any]:
    agents = {a["id"]: a for a in spec["agents"]}
    nodes = []
    for scenario, agent, sample in cells(spec):
        node = {"id": node_id(scenario, agent, sample),
                "objective": f"按 TASK.md 处理 scenarios/{scenario}/CONTEXT.md 的冻结场景，只读，只输出规定的 JSON。",
                "executor": agent, "needs": [], "contextRefs": ["TASK.md", "RULE.md", f"scenarios/{scenario}/"],
                "acceptance": [f"交付物是 TASK.md 规定的单个 JSON 对象，scenario 为 {scenario}，不超过 1500 字符"],
                "output": {"name": f"{node_id(scenario, agent, sample)}-choice", "format": "json"}}
        chosen = selection(spec, arm, agents[agent])
        if chosen:
            node["selection"] = chosen
        nodes.append(node)
    target = next(a for a in spec["agents"] if a.get("target"))
    nodes.append({"id": "done", "objective": "上游节点都已结束。不读取上游内容，直接输出 {\"done\": true}。",
                  "executor": target["id"], "needs": [n["id"] for n in nodes], "contextRefs": [],
                  "acceptance": ["输出 {\"done\": true}"], "output": {"name": "done", "format": "json"},
                  "selection": {**({"model": target["model"]} if target.get("model") else {}), "effort": "low"}})
    return {
        "schemaVersion": "RunIntent@1",
        "requestId": request_id,
        "objective": f"收集冻结场景下各 agent 按 RULE.md 作出的选择（rule-eval {spec['id']}）。",
        "acceptance": ["每个场景节点交付 TASK.md 规定的 JSON 对象，或如实失败"],
        "contextRefs": ["TASK.md"],
        "workspaceRef": f"file://{workspace}",
        "desiredEffect": "read",
        "terminalEvidence": ["done"],
        "graph": {"schemaVersion": "RunGraph@1",
                  "participants": {a["id"]: a["ref"] for a in spec["agents"]},
                  "limits": {"maxConcurrency": 6, "maxNodeAttempts": 1, "timeoutSeconds": spec["timeout_seconds"]},
                  "nodes": nodes, "resultNode": "done"},
    }


def rs_json(rs: Path, *args: str) -> dict[str, Any]:
    result = subprocess.run([str(rs), *args], capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = None
    if result.returncode != 0 or not isinstance(payload, dict):
        detail = (result.stderr or result.stdout).strip()[-600:]
        raise RuntimeError(f"rs {args[0]} {args[1]} exited {result.returncode}: {detail}")
    return payload


def find(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if value.get(key) is not None:
            return value[key]
        value = list(value.values())
    if isinstance(value, list):
        for item in value:
            found = find(item, key)
            if found is not None:
                return found
    return None


def spec_digest(base: Path, spec: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode())
    for path in sorted([*(base / arm_of(spec, arm)["rule"] for arm in ARMS),
                        *(base / "scenarios" / s["id"] / "CONTEXT.md" for s in spec["scenarios"])]):
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def start(args: argparse.Namespace) -> dict[str, Any]:
    spec_path = args.spec.resolve()
    spec, base = load_spec(spec_path), spec_path.parent
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / "runs" / stamp
    record: dict[str, Any] = {"schema": RUN_SCHEMA, "spec_id": spec["id"], "spec_digest": spec_digest(base, spec),
                              "created_at": stamp, "dry_run": args.dry_run, "run_dir": str(run_dir), "arms": {}}
    run_dir.mkdir(parents=True)
    # The spec snapshot travels with the run so later spec edits cannot change how this run is scored.
    (run_dir / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2))
    for arm in ARMS:
        workspace = build_workspace(run_dir / arm / "workspace", base, spec, arm)
        request_id = f"rule-eval-{spec['id']}-{arm}-{stamp}".lower()
        intent_path = run_dir / arm / "intent.json"
        intent_path.write_text(json.dumps(build_intent(spec, arm, workspace, request_id), ensure_ascii=False, indent=2))
        checked = rs_json(args.rs, "run", "validate", str(intent_path))
        if checked.get("status") != "valid":
            raise RuntimeError(f"intent invalid for {arm}: {json.dumps(checked, ensure_ascii=False)[:600]}")
        entry: dict[str, Any] = {"request_id": request_id, "intent": str(intent_path)}
        if not args.dry_run:
            started = rs_json(args.rs, "run", "start", str(intent_path))
            entry["run_id"] = find(started, "runId")
            if not entry["run_id"]:
                raise RuntimeError(f"run start returned no runId for {arm}: {json.dumps(started)[:400]}")
        record["arms"][arm] = entry
        # Written after each arm, so a failed second start still leaves the first Run findable.
        (run_dir / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    return record


def parse_choice(summary: Any, choices: list[str]) -> str | None:
    text = summary if isinstance(summary, str) else json.dumps(summary or {})
    match = re.search(r"\{.*\}", text, re.S)
    try:
        answer = json.loads(match.group(0)) if match else {}
        if isinstance(answer, dict) and "choice" not in answer and len(answer) == 1:
            answer = next(iter(answer.values()))
        choice = str(answer.get("choice", "")).strip().upper()
    except (ValueError, AttributeError):
        return None
    return choice if choice in choices else None


def verdict(spec: dict[str, Any], table: dict[str, dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if any(cell["status"] == "pending" for arm in table.values() for cell in arm.values()):
        return "pending", ["some scenario nodes have not finished"]
    target = next(a["id"] for a in spec["agents"] if a.get("target"))
    target_cells = [c for c in cells(spec) if c[1] == target]
    if any(table[arm][node_id(*c)]["choice"] is None for arm in ARMS for c in target_cells):
        return "inconclusive", ["a target-agent node failed or returned no valid choice"]
    wrong = [node_id(*c) for c in target_cells if not table["candidate"][node_id(*c)]["correct"]]
    if not wrong and all(table["baseline"][node_id(*c)]["correct"] for c in target_cells):
        # Without approval in the loop, a change with no measurable gain must not land.
        return "no_change", ["baseline already correct for every target cell"]
    if wrong:
        reasons.append("candidate wrong for target agent: " + ", ".join(wrong))
    regressed = []
    for agent in (a["id"] for a in spec["agents"]):
        # Compare only cells valid in both arms, so an unrelated provider failure cannot pass or fail the change.
        both = [node_id(*c) for c in cells(spec) if c[1] == agent
                and all(table[arm][node_id(*c)]["choice"] is not None for arm in ARMS)]
        old, new = (sum(table[arm][n]["correct"] for n in both) for arm in ARMS)
        if new < old:
            regressed.append(agent)
            reasons.append(f"candidate regresses for {agent}: {new}/{len(both)} vs baseline {old}/{len(both)}")
    if not reasons:
        return "pass", ["candidate correct for every target cell, no regression"]
    # Reaching here with no wrong target cell means the baseline missed one: the target improved, another agent got
    # worse. The rule fits only some agents, so scoping it per client is a human decision, not a rejection.
    return ("split" if not wrong and regressed else "fail"), reasons


def collect(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir.resolve()
    record = json.loads((run_dir / "run.json").read_text())
    if record.get("dry_run"):
        raise SpecError("dry-run records have no Runs to collect")
    spec = json.loads((run_dir / "spec.json").read_text())
    expected = {s["id"]: s for s in spec["scenarios"]}
    table: dict[str, dict[str, Any]] = {}
    runs: dict[str, Any] = {}
    for arm in ARMS:
        run_id = record["arms"][arm]["run_id"]
        inspected = rs_json(args.rs, "run", "inspect", run_id)
        run_status = (inspected.get("summary") or {}).get("status")
        nodes = {n["node"]["id"]: n for n in inspected.get("graphNodes") or []}
        table[arm] = {}
        for scenario, agent, sample in cells(spec):
            node = nodes.get(node_id(scenario, agent, sample)) or {}
            status = node.get("status")
            done = status in DONE_NODE or run_status in DONE_RUN
            choice = parse_choice((node.get("value") or {}).get("summary"), expected[scenario]["choices"]) if done else None
            table[arm][node_id(scenario, agent, sample)] = {
                "status": status if done else "pending", "choice": choice,
                "correct": choice == expected[scenario]["expected"]}
        finished = all(c["status"] != "pending" for c in table[arm].values())
        cancelled = False
        # The terminal "done" node may stall the Run in needs_human; cancel only this experiment's own Run.
        if finished and run_status not in FINAL_RUN and args.cancel_unfinished:
            rs_json(args.rs, "run", "cancel", run_id)
            cancelled = True
        runs[arm] = {"run_id": run_id, "status": run_status, "cancelled": cancelled}
    outcome, reasons = verdict(spec, table)
    scores = {arm: {agent["id"]: f"{sum(table[arm][node_id(*c)]['correct'] for c in cells(spec) if c[1] == agent['id'])}"
                    f"/{len(spec['scenarios']) * spec['samples']}" for agent in spec["agents"]} for arm in ARMS}
    result = {"schema": RESULT_SCHEMA, "contract": "analysis data; verdict rules in docs/runbook/rule-eval.md",
              "spec_id": spec["id"], "spec_digest": record["spec_digest"], "verdict": outcome, "reasons": reasons,
              "scores": scores, "runs": runs, "cells": table}
    if outcome != "pending":
        (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        result["result_file"] = str(run_dir / "result.json")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("start", help="build one workspace and DAG Run per arm, then start both Runs")
    run.add_argument("spec", type=Path, help="path to spec.json")
    run.add_argument("--dry-run", action="store_true", help="build workspaces and validate intents without starting")
    run.add_argument("--rs", type=Path, default=default_rs())
    run.set_defaults(handler=start)
    take = commands.add_parser("collect", help="read node choices of a started run directory and score them")
    take.add_argument("run_dir", type=Path)
    take.add_argument("--no-cancel", dest="cancel_unfinished", action="store_false",
                      help="keep a finished experiment Run that is still non-terminal")
    take.add_argument("--rs", type=Path, default=default_rs())
    take.set_defaults(handler=collect)
    usage = commands.add_parser("usage", help="local call statistics")
    usage.set_defaults(handler=lambda _args: cli_usage.summarize(CLI, COMMANDS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started, code = time.monotonic(), 0
    try:
        print(json.dumps(args.handler(args), ensure_ascii=False, indent=2))
    except SpecError as exc:
        print(json.dumps({"schema": RESULT_SCHEMA, "error": "spec", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        code = 2
    except (OSError, RuntimeError, subprocess.CalledProcessError, KeyError) as exc:
        print(json.dumps({"schema": RESULT_SCHEMA, "error": type(exc).__name__, "detail": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        code = 1
    cli_usage.record(CLI, args.command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
