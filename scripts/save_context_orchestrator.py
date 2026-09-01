#!/usr/bin/env python3
"""Compose save-context helpers into one checkpoint invocation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
RunCommand = Callable[[list[str], str | None], subprocess.CompletedProcess[str]]
ADMISSION_SCHEMA = "save-context.admission.v1"
ADMISSION_DECISIONS = {"checkpoint_ready", "continue_work"}
MAX_ADMISSION_BYTES = 16 * 1024
MAX_ADMISSION_ITEMS = 20
MAX_ADMISSION_ITEM_LENGTH = 500


@dataclass(frozen=True)
class Commands:
    audit: tuple[str, ...] = (
        sys.executable,
        str(SCRIPT_DIR / "save_context_audit_rs.py"),
    )
    context: tuple[str, ...] = (
        sys.executable,
        str(SCRIPT_DIR / "save_context.py"),
    )
    title: tuple[str, ...] = (
        sys.executable,
        str(SCRIPT_DIR / "codex_session_titles.py"),
    )


def run_command(
    command: list[str], input_text: str | None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return subprocess.CompletedProcess(
            command,
            126,
            "",
            f"cannot start helper {command[0]}: {error}",
        )


def compact_detail(completed: subprocess.CompletedProcess[str]) -> str:
    detail = completed.stderr.strip() or completed.stdout.strip()
    return detail[-500:]


def parse_admission(content: str) -> dict[str, Any]:
    if len(content.encode("utf-8")) > MAX_ADMISSION_BYTES:
        raise ValueError("admission exceeds 16 KiB")
    try:
        admission = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(f"admission returned invalid JSON: {error}") from error
    if not isinstance(admission, dict):
        raise ValueError("admission must be a JSON object")
    if admission.get("schema") != ADMISSION_SCHEMA:
        raise ValueError(f"admission schema must be {ADMISSION_SCHEMA}")
    decision = admission.get("decision")
    if decision not in ADMISSION_DECISIONS:
        raise ValueError(
            "admission decision must be checkpoint_ready or continue_work"
        )
    checked = admission.get("checked")
    actionable = admission.get("actionable")
    if (
        not isinstance(checked, list)
        or not checked
        or len(checked) > MAX_ADMISSION_ITEMS
        or not all(
            isinstance(item, str)
            and item.strip()
            and len(item) <= MAX_ADMISSION_ITEM_LENGTH
            for item in checked
        )
    ):
        raise ValueError("admission checked must be a non-empty string list")
    if (
        not isinstance(actionable, list)
        or len(actionable) > MAX_ADMISSION_ITEMS
        or not all(
            isinstance(item, str)
            and item.strip()
            and len(item) <= MAX_ADMISSION_ITEM_LENGTH
            for item in actionable
        )
    ):
        raise ValueError("admission actionable must be a string list")
    if decision == "checkpoint_ready" and actionable:
        raise ValueError("checkpoint_ready admission cannot contain actionable items")
    if decision == "continue_work" and not actionable:
        raise ValueError("continue_work admission requires actionable items")
    return admission


def read_admission(path: str) -> dict[str, Any]:
    try:
        admission_path = Path(path).expanduser()
        if admission_path.stat().st_size > MAX_ADMISSION_BYTES:
            raise ValueError("admission exceeds 16 KiB")
        content = admission_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"cannot read admission file {path}: {error}") from error
    return parse_admission(content)


def admission_stage(
    admission: dict[str, Any], pause_override: bool
) -> tuple[dict[str, Any], bool]:
    decision = admission["decision"]
    actionable = admission["actionable"]
    if pause_override and decision != "continue_work":
        raise ValueError(
            "--pause-override requires admission decision continue_work"
        )
    if decision == "continue_work" and not pause_override:
        return ({
            "status": "blocked",
            "decision": decision,
            "checked_count": len(admission["checked"]),
            "actionable": actionable,
        }, False)
    return ({
        "status": "overridden" if pause_override else "succeeded",
        "decision": decision,
        "checked_count": len(admission["checked"]),
        **({"actionable": actionable} if actionable else {}),
    }, True)


def audit_stage(
    args: argparse.Namespace,
    commands: Commands,
    runner: RunCommand,
) -> dict[str, Any]:
    source = args.audit_thread_id or args.audit_rollout
    if not source:
        return {"status": "skipped", "reason": "not_requested"}

    command = [*commands.audit, "dispatch"]
    if args.audit_thread_id:
        command.extend(["--thread-id", args.audit_thread_id])
    else:
        command.extend(["--rollout", args.audit_rollout])
    command.extend(["--cwd", args.audit_cwd, "--route", args.abbr])
    if args.audit_ll:
        command.extend(["--ll", args.audit_ll])

    completed = runner(command, None)
    if completed.returncode != 0:
        return {
            "status": "failed",
            "exit_code": completed.returncode,
            "detail": compact_detail(completed),
        }
    try:
        receipt = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return {
            "status": "failed",
            "exit_code": 1,
            "detail": f"audit returned invalid JSON: {error}",
        }
    if not isinstance(receipt, dict):
        return {
            "status": "failed",
            "exit_code": 1,
            "detail": "audit returned JSON that is not an object",
        }
    return {
        "status": receipt.get("status", "pending"),
        **{
            key: receipt[key]
            for key in ("run_id", "receipt_path", "output_path", "steward")
            if key in receipt
        },
    }


def context_stage(
    context_args: list[str],
    input_text: str | None,
    commands: Commands,
    runner: RunCommand,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    completed = runner([*commands.context, *context_args], input_text)
    if completed.returncode != 0:
        return ({
            "status": "failed",
            "exit_code": completed.returncode,
            "detail": compact_detail(completed),
        }, completed)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return ({
        "status": "succeeded",
        "timeline": (
            "appended"
            if any(line.startswith("appended ") for line in lines)
            else "unchanged"
        ),
        "output": lines[-3:],
    }, completed)


def context_preflight_stage(
    context_args: list[str],
    input_text: str | None,
    commands: Commands,
    runner: RunCommand,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    completed = runner(
        [*commands.context, *context_args, "--validate-only"], input_text
    )
    if completed.returncode != 0:
        return ({
            "status": "failed",
            "exit_code": completed.returncode,
            "detail": compact_detail(completed),
        }, completed)
    return ({"status": "succeeded"}, completed)


def option_value(arguments: list[str], name: str) -> str:
    for index, argument in enumerate(arguments):
        if argument == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(f"{name}="):
            return argument.split("=", 1)[1]
    return ""


def has_option(arguments: list[str], name: str) -> bool:
    return any(
        argument == name or argument.startswith(f"{name}=")
        for argument in arguments
    )


def title_stage(
    refresh_title: bool,
    timeline_appended: bool,
    context_args: list[str],
    commands: Commands,
    runner: RunCommand,
) -> dict[str, Any]:
    if not refresh_title:
        return {"status": "skipped", "reason": "not_requested"}
    command = [*commands.title, "--current"]
    timeline = option_value(context_args, "--timeline")
    if timeline_appended and timeline:
        command.extend(["--daily-note-title", timeline])
    completed = runner(command, None)
    if completed.returncode != 0:
        return {
            "status": "failed",
            "exit_code": completed.returncode,
            "detail": compact_detail(completed),
        }
    return {
        "status": "succeeded",
        "detail": compact_detail(completed),
    }


def orchestrate(
    args: argparse.Namespace,
    context_args: list[str],
    input_text: str | None,
    admission: dict[str, Any],
    commands: Commands = Commands(),
    runner: RunCommand = run_command,
) -> tuple[int, dict[str, Any]]:
    stages: dict[str, Any] = {}
    stages["admission"], admitted = admission_stage(
        admission, args.pause_override
    )
    if not admitted:
        for name in ("preflight", "audit", "context", "title"):
            stages[name] = {"status": "skipped", "reason": "continue_work"}
        return 3, {
            "schema": "save-context.checkpoint.v1",
            "status": "continue_work",
            "stages": stages,
        }
    stages["preflight"], preflight_result = context_preflight_stage(
        context_args, input_text, commands, runner
    )
    if preflight_result.returncode != 0:
        for name in ("audit", "context", "title"):
            stages[name] = {"status": "skipped", "reason": "preflight_failed"}
        return preflight_result.returncode, {
            "schema": "save-context.checkpoint.v1",
            "status": "failed",
            "stages": stages,
        }

    stages["audit"] = audit_stage(args, commands, runner)
    stages["context"], context_result = context_stage(
        context_args, input_text, commands, runner
    )
    if context_result.returncode != 0:
        stages["title"] = {"status": "skipped", "reason": "context_failed"}
        return context_result.returncode, {
            "schema": "save-context.checkpoint.v1",
            "status": "failed",
            "stages": stages,
        }

    stages["title"] = title_stage(
        args.refresh_title,
        stages["context"]["timeline"] == "appended",
        context_args,
        commands,
        runner,
    )
    degraded = any(
        stage["status"] == "failed"
        for name, stage in stages.items()
        if name != "context"
    )
    return 0, {
        "schema": "save-context.checkpoint.v1",
        "status": "degraded" if degraded else "succeeded",
        "stages": stages,
    }


def orchestration_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--orchestrate", action="store_true")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--audit-thread-id")
    source.add_argument("--audit-rollout")
    parser.add_argument("--audit-cwd")
    parser.add_argument("--audit-ll")
    parser.add_argument("--admission-file")
    parser.add_argument("--pause-override", action="store_true")
    parser.add_argument("--refresh-title", action="store_true")
    return parser


def main() -> int:
    parser = orchestration_parser()
    args, context_args = parser.parse_known_args()
    if not args.orchestrate:
        os.execv(
            sys.executable,
            [sys.executable, str(SCRIPT_DIR / "save_context.py"), *sys.argv[1:]],
        )
    if not context_args or context_args[0].startswith("-"):
        parser.error("orchestrated save requires <abbr> before context options")
    if not args.admission_file:
        parser.error("orchestrated save requires --admission-file")
    if "--validate-only" in context_args:
        parser.error("--validate-only is reserved for orchestrator preflight")
    args.abbr = context_args[0]
    mainline_context_input = (
        ":" not in args.abbr
        and (
            has_option(context_args, "--context-file")
            or has_option(context_args, "--context-stdin")
        )
        and not has_option(context_args, "--allow-empty")
    )
    if mainline_context_input and not has_option(context_args, "--next-route"):
        parser.error(
            "orchestrated mainline save requires --next-route "
            "<none|mainline|existing-workstream>"
        )
    if (args.audit_thread_id or args.audit_rollout) and not args.audit_cwd:
        parser.error("--audit-cwd is required with an audit source")
    if args.audit_cwd and not (args.audit_thread_id or args.audit_rollout):
        parser.error("--audit-cwd requires --audit-thread-id or --audit-rollout")

    needs_stdin = "--context-stdin" in context_args or (
        option_value(context_args, "--context-file") == "-"
    )
    input_text = sys.stdin.read() if needs_stdin else None
    try:
        admission = read_admission(args.admission_file)
        exit_code, receipt = orchestrate(
            args, context_args, input_text, admission
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
