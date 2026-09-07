#!/usr/bin/env python3
"""Write project context and optionally append a Daily Note timeline entry.

Mainline saves accept a complete context.v2 document. Workstream saves accept a
context.workstream.v1 payload and merge only that route into the project file.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from context_ff_merge import (
    load_context,
    load_yaml_module,
    render_context,
    split_context,
)

CONTEXT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ROUTE_INDEX_RE = re.compile(r"^# context: .+$")
REQUIRED_FRONTMATTER_KEYS = {
    "schema",
    "project",
    "mainline",
    "workstreams",
    "next_route",
    "updated",
}
REQUIRED_WORKSTREAM_KEYS = {
    "schema",
    "state",
    "summary",
    "doing",
    "blocked",
    "next_step",
    "details",
}
WORKSTREAM_STATES = {"active", "parked", "blocked", "closure-candidate"}
REMOVED_ROUTE_KEYS = {"selected_route", "active_route"}


def context_path(spec: str) -> tuple[Path, str]:
    parts = spec.split(":", 1)
    abbr = parts[0].strip()
    workstream = parts[1].strip() if len(parts) == 2 else ""

    if not CONTEXT_NAME_RE.match(abbr):
        raise ValueError(f"invalid context abbr: {abbr!r}")
    if workstream and not CONTEXT_NAME_RE.match(workstream):
        raise ValueError(f"invalid context workstream: {workstream!r}")

    context_dir = Path.home() / ".ai" / "contexts"
    return context_dir / f"{abbr}.md", workstream


def daily_note_path(now: datetime) -> Path:
    return (Path.home() / "Documents" / "me" / "Daily Notes" /
            f"{now.month:02d}" / f"{now.month:02d}-{now.day:02d}.md")


def chinese_weekday(now: datetime) -> str:
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return names[now.weekday()]


def ensure_daily_note(path: Path, now: datetime) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")

    path.parent.mkdir(parents=True, exist_ok=True)
    return f"# {now.month}月{now.day}日\n\n## {now.year} {chinese_weekday(now)}\n\n### Timeline\n\n"


def append_timeline(daily: str, entry: str) -> tuple[str, bool]:
    if "### Timeline" not in daily:
        daily = daily.rstrip() + "\n\n### Timeline\n\n"

    line = f"- {entry}"

    def normalized_timeline_text(value: str) -> str:
        value = value.strip()
        value = re.sub(r"^- ", "", value)
        value = re.sub(r"^\[\d{2}:\d{2}-\d{2}:\d{2}\]\s+", "", value)
        value = re.sub(r"^\d{2}:\d{2}\s+", "", value)
        return value

    existing = {
        normalized_timeline_text(existing_line)
        for existing_line in daily.splitlines()
    }
    if normalized_timeline_text(line) in existing:
        return daily, False

    return daily.rstrip() + "\n" + line + "\n", True


def read_context(args: argparse.Namespace) -> str:
    if args.context_stdin or args.context_file == "-":
        return sys.stdin.read()

    context_source = Path(args.context_file)
    return context_source.read_text(encoding="utf-8")


def split_context_frontmatter(context: str) -> tuple[str, str]:
    lines = context.splitlines()
    if not lines:
        raise ValueError("context input is empty")
    if lines[0].strip() != "---":
        raise ValueError(
            "context first line must open YAML frontmatter with ---")
    if len(lines) < 2:
        raise ValueError("context second line must be a route index comment")
    route_index = lines[1].strip()
    if not ROUTE_INDEX_RE.match(route_index):
        raise ValueError("context second line must be a route index comment")
    if "project=" not in route_index or "mainline=" not in route_index:
        raise ValueError("context route index is missing project/mainline")
    if "workstreams=" not in route_index or "next=" not in route_index:
        raise ValueError("context route index is missing workstreams/next")

    delimiter_lines = [
        index for index, line in enumerate(lines[2:], start=2)
        if line.strip() == "---"
    ]
    if not delimiter_lines:
        raise ValueError("context must contain YAML frontmatter delimiters")

    end = delimiter_lines[0]
    frontmatter = "\n".join(lines[1:end])
    if not frontmatter.strip():
        raise ValueError("context YAML frontmatter is empty")
    return route_index, frontmatter


def fallback_parse_frontmatter(frontmatter: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line_number, line in enumerate(frontmatter.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise ValueError(
                f"context YAML line {line_number} contains a tab")
        if len(line) - len(line.lstrip(" ")) == 0:
            if ":" not in line:
                raise ValueError(
                    f"context YAML line {line_number} is not a mapping")
            key, value = line.split(":", 1)
            key = key.strip()
            if key:
                value = value.strip()
                if value == "{}":
                    data[key] = {}
                else:
                    data[key] = value or {}
        stripped = line.strip()
        if not (":" in stripped or stripped.startswith("- ")):
            raise ValueError(
                f"context YAML line {line_number} is not a mapping or list item")
    return data


def parse_frontmatter(frontmatter: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        parsed = fallback_parse_frontmatter(frontmatter)
    else:
        try:
            loaded = yaml.safe_load(frontmatter)
        except yaml.YAMLError as exc:
            raise ValueError(f"context YAML is invalid: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError("context YAML frontmatter must be a mapping")
        parsed = loaded

    removed = sorted(REMOVED_ROUTE_KEYS.intersection(parsed))
    if removed:
        raise ValueError("context YAML contains removed route key(s): " +
                         ", ".join(removed))
    missing = sorted(REQUIRED_FRONTMATTER_KEYS.difference(parsed))
    if missing:
        raise ValueError(
            "context YAML missing required key(s): " + ", ".join(missing))
    if parsed.get("schema") != "context.v2":
        raise ValueError("context YAML schema must be context.v2")
    if not isinstance(parsed.get("mainline"), dict):
        raise ValueError("context YAML mainline must be a mapping")
    if not isinstance(parsed.get("workstreams"), dict):
        raise ValueError("context YAML workstreams must be a mapping")
    next_route = parsed.get("next_route")
    if (next_route is not None and next_route != "mainline" and
            (not isinstance(next_route, str)
             or next_route not in parsed["workstreams"])):
        raise ValueError(f"context YAML next_route {next_route!r} does not exist")
    return parsed


def validate_context_structure(parser: argparse.ArgumentParser, context: str,
                               abbr: str) -> None:
    try:
        route_index, frontmatter = split_context_frontmatter(context)
        parsed = parse_frontmatter(frontmatter)
    except ValueError as exc:
        parser.error(str(exc))

    project = str(parsed.get("project", ""))
    expected_project = abbr.split(":", 1)[0]
    if project != expected_project:
        parser.error(
            f"context YAML project {project!r} does not match abbr {expected_project!r}"
        )
    if f"project={project}" not in route_index:
        parser.error("context route index project does not match YAML project")
    indexed_next_route = route_index.rsplit("next=", 1)[-1].strip()
    expected_next_route = parsed.get("next_route") or "none"
    if indexed_next_route != expected_next_route:
        parser.error("context route index next does not match YAML next_route")


def validate_context_input(parser: argparse.ArgumentParser, context: str,
                           allow_empty: bool, abbr: str) -> None:
    if context.strip():
        validate_context_structure(parser, context, abbr)
        return

    if allow_empty:
        return

    parser.error(
        "context input is empty; refusing to overwrite context snapshot "
        "without --allow-empty")


def parse_workstream_payload(text: str) -> tuple[dict[str, Any], str]:
    if not text.strip():
        raise ValueError("workstream input is empty")
    yaml = load_yaml_module()
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"workstream YAML is invalid: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("workstream payload must be a mapping")

    missing = sorted(REQUIRED_WORKSTREAM_KEYS.difference(loaded))
    if missing:
        raise ValueError("workstream payload missing required key(s): " +
                         ", ".join(missing))
    unknown = sorted(set(loaded).difference(REQUIRED_WORKSTREAM_KEYS))
    if unknown:
        raise ValueError("workstream payload has unknown key(s): " +
                         ", ".join(unknown))
    if loaded.get("schema") != "context.workstream.v1":
        raise ValueError("workstream schema must be context.workstream.v1")
    if loaded.get("state") not in WORKSTREAM_STATES:
        raise ValueError("workstream state must be active, parked, blocked, or "
                         "closure-candidate")
    if loaded.get("summary") is not None and not isinstance(
            loaded.get("summary"), str):
        raise ValueError("workstream summary must be a string or null")
    if not isinstance(loaded.get("doing"), list):
        raise ValueError("workstream doing must be a list")
    if not isinstance(loaded.get("blocked"), list):
        raise ValueError("workstream blocked must be a list")
    details = loaded.get("details")
    if not isinstance(details, str) or not details.strip():
        raise ValueError("workstream details must be non-empty Markdown")

    route_data = {
        key: loaded[key]
        for key in ("state", "summary", "doing", "blocked", "next_step")
    }
    return route_data, details.strip()


def merge_workstream_details(body: str, workstream: str, details: str,
                             workstream_names: set[str]) -> str:
    lines = body.splitlines()
    heading = f"### {workstream}"
    section = [heading, "", *details.splitlines()]
    try:
        start = next(index for index, line in enumerate(lines)
                     if line.strip() == heading)
    except StopIteration:
        if not any(line.strip() == "## Workstreams" for line in lines):
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(["## Workstreams", ""])
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(section)
        return "\n".join(lines).rstrip() + "\n"

    other_headings = {
        f"### {name}" for name in workstream_names if name != workstream
    }
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped in other_headings or stripped.startswith("## "):
            end = index
            break
    replacement = section + ([""] if end < len(lines) else [])
    return "\n".join(lines[:start] + replacement + lines[end:]).rstrip() + "\n"


def merge_workstream(path: Path, abbr: str, workstream: str, text: str) -> str:
    route_data, details = parse_workstream_payload(text)
    data, body = load_context(path, abbr)
    workstreams = data["workstreams"]
    workstreams[workstream] = route_data
    data["next_route"] = workstream
    data["updated"] = datetime.now().date().isoformat()
    body = merge_workstream_details(body, workstream, details,
                                    set(workstreams))
    return render_context(data, body)


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "abbr",
        help=
        "Project abbreviation, optionally with workstream route, e.g. sma or amt:agent-doc-hygiene",
    )
    parser.add_argument(
        "--context-file",
        required=False,
        help=
        ("File containing full context markdown for mainline or a "
         "context.workstream.v1 payload for abbr:workstream; '-' reads stdin"),
    )
    parser.add_argument(
        "--context-stdin",
        action="store_true",
        help=("Read full context markdown for mainline or a "
              "context.workstream.v1 payload for abbr:workstream from stdin"),
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow writing an empty context snapshot",
    )
    parser.add_argument(
        "--timeline",
        default="",
        help="One-line Daily Note timeline text without leading '- '",
    )
    parser.add_argument(
        "--date",
        default="",
        help="Daily Note date in YYYY-MM-DD. Defaults to today.",
    )
    parser.add_argument(
        "--skip-timeline",
        action="store_true",
        help="Only update context; do not append Daily Note timeline",
    )
    parser.add_argument(
        "--timeline-only",
        action="store_true",
        help="Only append Daily Note timeline; do not write context",
    )
    parser.add_argument(
        "--delete-context",
        action="store_true",
        help="Delete the target context snapshot instead of writing it",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and compile inputs without writing context or timeline files",
    )
    args = parser.parse_args()

    if args.timeline_only and args.skip_timeline:
        parser.error("--timeline-only cannot be used with --skip-timeline")

    context_input_count = int(bool(args.context_file)) + int(args.context_stdin)

    if args.delete_context and context_input_count:
        parser.error("--delete-context cannot be used with context input")

    if args.timeline_only and args.delete_context:
        parser.error("--timeline-only cannot be used with --delete-context")

    if context_input_count > 1:
        parser.error(
            "use only one context input: --context-file or --context-stdin")

    if not args.timeline_only and not args.delete_context and not context_input_count:
        parser.error("context input is required unless --timeline-only is set")

    path = None
    workstream = ""
    if not args.timeline_only:
        try:
            path, workstream = context_path(args.abbr)
        except ValueError as exc:
            parser.error(str(exc))

    context: str | None = None
    if not args.timeline_only and not args.delete_context:
        context = read_context(args)
        assert path is not None
        if workstream:
            if args.allow_empty:
                parser.error("--allow-empty is not valid for a workstream save")
            try:
                context = merge_workstream(path, args.abbr.split(":", 1)[0],
                                           workstream, context)
            except (OSError, ValueError) as exc:
                parser.error(str(exc))
        else:
            validate_context_input(parser, context, args.allow_empty, args.abbr)

    timeline_now: datetime | None = None
    if not args.skip_timeline and args.timeline.strip():
        if args.date:
            try:
                timeline_now = datetime.strptime(args.date, "%Y-%m-%d")
            except ValueError:
                parser.error("--date must be in YYYY-MM-DD format")
        else:
            timeline_now = datetime.now()

    if args.validate_only:
        print("validation succeeded")
        return 0

    if args.timeline_only:
        print("context skipped")
    elif args.delete_context:
        if workstream:
            parser.error(
                "--delete-context cannot delete a single workstream in context.v2; "
                "rewrite the project context without that workstream")
        assert path is not None
        if path.exists():
            path.unlink()
            print(f"deleted {path}")
        else:
            print(f"context already missing {path}")
    else:
        assert context is not None
        assert path is not None
        if workstream:
            atomic_write_text(path, context)
            print(f"merged workstream {workstream} into {path}")
        else:
            atomic_write_text(path, context)
            print(f"wrote {path}")

    if args.skip_timeline or not args.timeline.strip():
        print("timeline skipped")
        return 0

    assert timeline_now is not None
    now = timeline_now
    path = daily_note_path(now)
    daily = ensure_daily_note(path, now)
    daily, appended = append_timeline(daily, args.timeline.strip())
    if appended:
        path.write_text(daily, encoding="utf-8")
        print(f"appended {path}: - {args.timeline.strip()}")
    else:
        print(f"timeline already exists {path}: - {args.timeline.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
