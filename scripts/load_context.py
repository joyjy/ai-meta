#!/usr/bin/env python3
"""Select one load-context route projection from a context.v3 snapshot.

Read-only: it never writes the context, prunes registrations or refreshes remote state. The
load-context skill owns route rules, presentation and the follow-up probes.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402
from context_ff_merge import load_context, load_yaml_module, split_spec  # noqa: E402

CLI = "load-context"
COMMANDS = ["select", "usage"]
SCHEMA = "load-context.projection.v1"
TEMP_ROOTS = ("/private/tmp/", "/tmp/", "/private/var/folders/", "/var/folders/")
BACKTICK_PATH_RE = re.compile(r"`(/[^`\s]+)`")


class LoadError(Exception):
    def __init__(self, category: str, message: str, **fields: Any) -> None:
        super().__init__(message)
        self.payload = {"error": category, "message": message, **fields}


def resolve_route(route: str | None, cwd: Path) -> tuple[str, dict[str, Any]]:
    """Use the explicit route, else let GTD's project index resolver bind exactly one project."""
    if route:
        return route, {"by": "explicit"}
    gtd = Path.home() / ".ai" / "scripts" / "gtd"
    try:
        completed = subprocess.run([str(gtd), "project", "resolve", "--cwd", str(cwd)],
                                   capture_output=True, text=True, check=False)
    except OSError as exc:
        raise LoadError("gtd_unavailable", f"cannot start {gtd}: {exc.strerror}",
                        errno=errno.errorcode.get(exc.errno or 0, exc.errno)) from exc
    try:
        resolved = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LoadError("gtd_failed", "gtd project resolve did not return JSON",
                        exit_code=completed.returncode,
                        detail=completed.stderr.strip()[-300:]) from exc
    projects = resolved.get("projects") or []
    if resolved.get("status") != "OK" or len(projects) != 1:
        raise LoadError("route_unresolved",
                        "cwd does not resolve to exactly one project; pass <abbr> explicitly",
                        cwd=str(cwd), status=resolved.get("status"), reason=resolved.get("error"),
                        candidates=[project.get("abbr") for project in projects])
    return projects[0]["abbr"], {"by": "gtd project resolve", "entry": projects[0].get("entry")}


def section(body: str, heading: str, stops: set[str]) -> str | None:
    """Return the text under `heading` up to the next stop heading or level-2 heading."""
    lines = body.splitlines()
    start = next((index for index, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return None
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].strip() in stops or lines[index].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1:end]).strip()


def temporary_paths(markdown: str) -> list[dict[str, Any]]:
    """lstat backticked temp-root paths; only ENOENT counts as missing."""
    roots = TEMP_ROOTS + tuple(filter(None, [os.environ.get("TMPDIR")]))
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in BACKTICK_PATH_RE.finditer(markdown):
        path = match.group(1)
        if path in seen or not path.startswith(roots):
            continue
        seen.add(path)
        try:
            os.lstat(path)
            results.append({"path": path, "status": "exists"})
        except FileNotFoundError:
            results.append({"path": path, "status": "missing"})
        except OSError as exc:
            results.append({"path": path, "status": "unverified",
                            "errno": errno.errorcode.get(exc.errno or 0, exc.errno)})
    return results


def select(args: argparse.Namespace) -> dict[str, Any]:
    route, resolution = resolve_route(args.route, args.cwd)
    try:
        abbr, workstream = split_spec(route)
    except ValueError as exc:
        raise LoadError("route_invalid", str(exc)) from exc
    contexts = Path.home() / ".ai" / "contexts"
    path = contexts / f"{abbr}.md"
    if not path.exists():
        raise LoadError("context_missing", f"{path} does not exist; run /save-context {abbr} first",
                        path=str(path))
    try:
        data, body = load_context(path, abbr)
    except (OSError, ValueError, load_yaml_module().YAMLError) as exc:
        raise LoadError("context_invalid", str(exc), path=str(path)) from exc

    workstreams = data["workstreams"]
    projection: dict[str, Any] = {
        "schema": SCHEMA,
        "route": f"{abbr}:{workstream}" if workstream else abbr,
        "resolution": resolution,
        "context_path": str(path),
        "goal": data.get("goal"),
        "updated": data.get("updated"),
    }
    if workstream:
        if workstream not in workstreams:
            legacy = contexts / abbr / f"{workstream}.md"
            raise LoadError("workstream_missing", f"workstream {workstream!r} is not in {path}",
                            route=projection["route"], available=sorted(workstreams),
                            **({"legacy_path": str(legacy)} if legacy.exists() else {}))
        record = workstreams[workstream]
        markdown = section(body, f"### {workstream}",
                           {f"### {name}" for name in workstreams if name != workstream})
    else:
        record = data["mainline"]
        markdown = section(body, "## Mainline", set())
        projection["workstreams"] = [
            {"name": name, "state": item.get("state"), "summary": item.get("summary")}
            for name, item in workstreams.items()
        ]
    projection["selected"] = record
    projection["markdown"] = markdown
    projection["temporary_paths"] = temporary_paths(markdown or "")
    return projection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("select", help="emit the selected route projection as JSON")
    run.add_argument("route", nargs="?",
                     help="<abbr> or <abbr>:<workstream>; omitted resolves --cwd via gtd project resolve")
    run.add_argument("--cwd", type=Path, default=Path.cwd())
    run.set_defaults(handler=select)
    usage = commands.add_parser("usage", help="local call statistics")
    usage.set_defaults(handler=lambda _args: cli_usage.summarize(CLI, COMMANDS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started, code = time.monotonic(), 0
    try:
        print(json.dumps(args.handler(args), ensure_ascii=False, indent=2, default=str))
    except LoadError as exc:
        print(json.dumps(exc.payload, ensure_ascii=False), file=sys.stderr)
        code = 2
    cli_usage.record(CLI, args.command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
