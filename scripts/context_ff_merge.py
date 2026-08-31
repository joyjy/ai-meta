#!/usr/bin/env python3
"""Merge one final-form work order into a context.v2 snapshot."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

CONTEXT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REMOVED_ROUTE_KEYS = {"selected_route", "active_route"}


def load_yaml_module() -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError(
            "YAML support is required for context-ff-merge") from exc
    return yaml


def split_spec(spec: str) -> tuple[str, str]:
    parts = spec.split(":", 1)
    abbr = parts[0].strip()
    route = parts[1].strip() if len(parts) == 2 else ""
    if not CONTEXT_NAME_RE.match(abbr):
        raise ValueError(f"invalid context abbr: {abbr!r}")
    if route and not CONTEXT_NAME_RE.match(route):
        raise ValueError(f"invalid context route: {route!r}")
    return abbr, route


def read_ff(path: Path) -> dict[str, Any]:
    text = sys.stdin.read() if str(path) == "-" else path.read_text(
        encoding="utf-8")
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        yaml = load_yaml_module()
        loaded = yaml.safe_load(text)

    ff = unwrap_ff(loaded)
    if "origin_session_id" not in ff:
        ff["origin_session_id"] = os.environ.get("CODEX_THREAD_ID") or None
    validate_ff(ff)
    return ff


def unwrap_ff(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, dict) and set(value) == {"ff"}:
        value = value["ff"]
    if not isinstance(value, dict):
        raise ValueError("ff input must be an object, {'ff': object}, or - ff")
    return value


def validate_ff(ff: dict[str, Any]) -> None:
    if ff.get("output_target") != "context":
        raise ValueError("ff.output_target must equal 'context'")
    if not str(ff.get("goal", "")).strip():
        raise ValueError("ff.goal is required")
    if "blocking_questions" not in ff:
        raise ValueError("ff.blocking_questions is required")
    if "ready_for_dispatch" not in ff:
        raise ValueError("ff.ready_for_dispatch is required")


def split_context(text: str) -> tuple[str, str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(
            "context first line must open YAML frontmatter with ---")
    if len(lines) < 2 or not lines[1].startswith("# context: "):
        raise ValueError("context second line must be a route index comment")
    delimiters = [
        index for index, line in enumerate(lines[2:], start=2)
        if line.strip() == "---"
    ]
    if not delimiters:
        raise ValueError("context must contain YAML frontmatter delimiters")
    end = delimiters[0]
    frontmatter = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:])
    if body:
        body += "\n"
    return lines[1], frontmatter, body


def load_context(path: Path, abbr: str) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return minimal_context(abbr), f"# {abbr} Context\n\n## Mainline\n"

    yaml = load_yaml_module()
    _, frontmatter, body = split_context(path.read_text(encoding="utf-8"))
    data = yaml.safe_load(frontmatter)
    if not isinstance(data, dict):
        raise ValueError("context YAML frontmatter must be a mapping")
    if data.get("schema") != "context.v2":
        raise ValueError("context YAML schema must be context.v2")
    removed = sorted(REMOVED_ROUTE_KEYS.intersection(data))
    if removed:
        raise ValueError("context YAML contains removed route key(s): " +
                         ", ".join(removed))
    if "next_route" not in data:
        raise ValueError("context YAML missing required key: next_route")
    if data.get("project") != abbr:
        raise ValueError(
            f"context project {data.get('project')!r} does not match {abbr!r}")
    if not isinstance(data.get("mainline"), dict):
        raise ValueError("context mainline must be a mapping")
    if not isinstance(data.get("workstreams"), dict):
        raise ValueError("context workstreams must be a mapping")
    next_route = data.get("next_route")
    if (next_route is not None and next_route != "mainline" and
            (not isinstance(next_route, str)
             or next_route not in data["workstreams"])):
        raise ValueError(f"context next_route {next_route!r} does not exist")
    return data, body


def minimal_context(abbr: str) -> dict[str, Any]:
    return {
        "schema": "context.v2",
        "project": abbr,
        "goal": None,
        "mainline": {
            "state": "active",
            "summary": None,
            "doing": [],
            "blocked": [],
            "next_steps": [],
        },
        "workstreams": {},
        "next_route": "mainline",
        "updated": date.today().isoformat(),
    }


def merge_ff(data: dict[str, Any], route: str, ff: dict[str, Any],
             updated: str) -> None:
    data["next_route"] = route
    data["updated"] = updated
    if route == "mainline":
        mainline = data.setdefault("mainline", {})
        if not isinstance(mainline, dict):
            raise ValueError("context mainline must be a mapping")
        if mainline.get("state") in {None, "idle"}:
            mainline["state"] = "active"
        mainline["next_steps"] = [{"ff": ff}]
        return

    workstreams = data.setdefault("workstreams", {})
    if not isinstance(workstreams, dict):
        raise ValueError("context workstreams must be a mapping")
    workstream = workstreams.get(route)
    if workstream is None:
        workstream = {
            "state": "active",
            "summary": None,
            "doing": [],
            "blocked": [],
            "next_step": None,
        }
        workstreams[route] = workstream
    if not isinstance(workstream, dict):
        raise ValueError(f"context workstream {route!r} must be a mapping")
    if workstream.get("state") in {None, "idle"}:
        workstream["state"] = "active"
    workstream["next_step"] = {"ff": ff}


def mainline_has_recovery(mainline: dict[str, Any]) -> bool:
    return bool(mainline.get("doing") or mainline.get("blocked")
                or mainline.get("next_steps"))


def clear_completed_ff(data: dict[str, Any], route: str, expected_goal: str,
                       updated: str) -> bool:
    """Clear exactly one completed ff and return whether its route was removed."""
    expected_goal = expected_goal.strip()
    if not expected_goal:
        raise ValueError("--expect-goal is required with --clear-completed")

    if route == "mainline":
        mainline = data.get("mainline")
        if not isinstance(mainline, dict):
            raise ValueError("context mainline must be a mapping")
        next_steps = mainline.get("next_steps", [])
        if not isinstance(next_steps, list):
            raise ValueError("context mainline.next_steps must be a list")
        matches = [
            index for index, item in enumerate(next_steps)
            if isinstance(item, dict) and isinstance(item.get("ff"), dict)
            and str(item["ff"].get("goal", "")).strip() == expected_goal
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one matching mainline ff, found {len(matches)}"
            )
        del next_steps[matches[0]]
        mainline["next_steps"] = next_steps
        if not mainline_has_recovery(mainline):
            mainline["state"] = "idle"
            if data.get("next_route") == "mainline":
                data["next_route"] = None
    else:
        workstreams = data.get("workstreams")
        if not isinstance(workstreams, dict):
            raise ValueError("context workstreams must be a mapping")
        workstream = workstreams.get(route)
        if not isinstance(workstream, dict):
            raise ValueError(f"context workstream {route!r} does not exist")
        next_step = workstream.get("next_step")
        ff = next_step.get("ff") if isinstance(next_step, dict) else None
        goal = str(ff.get("goal", "")).strip() if isinstance(ff, dict) else ""
        if goal != expected_goal:
            raise ValueError(
                f"workstream {route!r} ff goal does not match --expect-goal")
        workstream["next_step"] = None
        if not workstream.get("doing") and not workstream.get("blocked"):
            del workstreams[route]
            if data.get("next_route") == route:
                mainline = data.get("mainline")
                if not isinstance(mainline, dict):
                    raise ValueError("context mainline must be a mapping")
                data["next_route"] = (
                    "mainline" if mainline_has_recovery(mainline) else None)
            data["updated"] = updated
            return True

    data["updated"] = updated
    return False


def remove_workstream_details(body: str, route: str,
                              remaining_routes: set[str]) -> str:
    """Remove an exact workstream detail section from the Markdown body."""
    lines = body.splitlines(keepends=True)
    section_start = next((index for index, line in enumerate(lines)
                          if line.strip() == "## Workstreams"), None)
    if section_start is None:
        return body
    section_end = next((index for index in range(section_start + 1, len(lines))
                        if lines[index].startswith("## ")), len(lines))

    if not remaining_routes:
        return "".join(lines[:section_start] + lines[section_end:])

    heading = f"### {route}"
    route_start = next((index for index in range(section_start + 1,
                                                 section_end)
                        if lines[index].strip() == heading), None)
    if route_start is None:
        return body
    remaining_headings = {f"### {name}" for name in remaining_routes}
    route_end = next((index for index in range(route_start + 1, section_end)
                      if lines[index].strip() in remaining_headings),
                     section_end)
    return "".join(lines[:route_start] + lines[route_end:])


def route_index(data: dict[str, Any]) -> str:
    workstreams = data.get("workstreams") if isinstance(
        data.get("workstreams"), dict) else {}
    states = []
    for name, item in workstreams.items():
        state = item.get("state", "active") if isinstance(item,
                                                          dict) else "active"
        states.append(f"{state}:{name}")
    mainline = data.get("mainline") if isinstance(data.get("mainline"),
                                                  dict) else {}
    mainline_state = mainline.get("state", "idle")
    next_route = data.get("next_route") or "none"
    return (f"# context: project={data.get('project')}; "
            f"mainline={mainline_state}; "
            f"workstreams={len(workstreams)}({', '.join(states)}); "
            f"next={next_route}")


def render_context(data: dict[str, Any], body: str) -> str:
    yaml = load_yaml_module()

    class IndentedSafeDumper(yaml.SafeDumper):

        def increase_indent(self, flow: bool = False,
                            indentless: bool = False) -> Any:
            return super().increase_indent(flow, False)

    frontmatter = yaml.dump(data,
                            Dumper=IndentedSafeDumper,
                            allow_unicode=True,
                            sort_keys=False,
                            default_flow_style=False,
                            width=10**9)
    return f"---\n{route_index(data)}\n{frontmatter}---\n\n{body}"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w",
                            encoding="utf-8",
                            dir=path.parent,
                            delete=False) as tmp:
        tmp.write(text)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge a final-form ff block into a context.v2 file.")
    parser.add_argument("abbr",
                        help="Context abbr, optionally abbr:workstream")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--ff-file", type=Path)
    action.add_argument("--clear-completed", action="store_true")
    parser.add_argument(
        "--expect-goal",
        help="Exact ff.goal to clear; required with --clear-completed",
    )
    parser.add_argument("--context-dir",
                        type=Path,
                        default=Path("~/.ai/contexts").expanduser())
    parser.add_argument("--route", help="Override target route")
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parser = parse_args(argv)
    try:
        abbr, spec_route = split_spec(parser.abbr)
        route = parser.route or spec_route or "mainline"
        if not CONTEXT_NAME_RE.match(route):
            raise ValueError(f"invalid context route: {route!r}")
        path = parser.context_dir.expanduser() / f"{abbr}.md"
        if parser.clear_completed and not path.exists():
            raise ValueError(f"context does not exist: {path}")
        data, body = load_context(path, abbr)
        if parser.clear_completed:
            removed_route = clear_completed_ff(data, route,
                                               parser.expect_goal or "",
                                               parser.date)
            if removed_route:
                body = remove_workstream_details(
                    body,
                    route,
                    set(data.get("workstreams", {})),
                )
        else:
            ff = read_ff(parser.ff_file)
            merge_ff(data, route, ff, parser.date)
        atomic_write_text(path, render_context(data, body))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    action = "cleared completed ff from" if parser.clear_completed else "merged ff into"
    print(f"{action} {path} route {route}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
