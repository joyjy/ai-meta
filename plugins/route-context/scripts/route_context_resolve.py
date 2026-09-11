#!/usr/bin/env python3
"""Resolve user shorthand into route context for agent injection."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
ME_ROOT = HOME / "Documents" / "me"
REPO_ROOT = Path(__file__).resolve().parents[3]

PROJECTS = {
    "amt": {
        "name": "ai-meta",
        "root": REPO_ROOT,
        "aliases": ("amt", "ai-meta", "ai meta"),
    },
    "gtd": {
        "name": "gtd",
        "root": ME_ROOT / "Projects" / "gtd",
        "aliases": ("gtd",),
    },
    "larkbot": {
        "name": "larkbot",
        "root": ME_ROOT / "Projects" / "larkbot",
        "aliases": ("larkbot",),
    },
}

DRAFT_DIR = ME_ROOT / "_Drafts"
SNIPPETS_DIR = ME_ROOT / "Snippets"

FORUM_SNIPPET_46 = {
    "id": "gitlab-project-snippet-46",
    "name": "Agent Forum GitLab project snippet source of truth",
    "url": "https://gitlab.example.com/example-org/dev/dev-flow-context/-/snippets/46",
    "gitlab_project_id": 15910,
    "gitlab_snippet_id": 46,
    "files": [
        "00-README.md",
        "01-flow.md",
        "10-prompt-daily-reflection.md",
        "11-prompt-thread-discussion.md",
        "12-prompt-promotion.md",
        "13-prompt-weekly-synthesis.md",
    ],
}

EN_DURABLE_DOC_RE = re.compile(
    r"\b(?:durable docs?|ADR|runbook|architecture docs?)\b",
    re.IGNORECASE,
)
ZH_DURABLE_DOC_TERMS = ("架构文档", "架构", "长期文档")
PLAN_RE = re.compile(r"(?<![\w-])plans?(?![\w-])", re.IGNORECASE)
DOCS_PLAN_RE = re.compile(r"(?<![\w-])docs/plans?(?![\w-])", re.IGNORECASE)
EN_PLAN_ARTIFACT_RE = re.compile(
    r"(?:create|write|save|add|draft|生成|创建|新建|写|写入|保存|落地)"
    r".{0,48}(?<![\w-])plans?(?![\w-])",
    re.IGNORECASE,
)
ZH_PLAN_ARTIFACT_RE = re.compile(
    r"(?:创建|新建|写|写入|保存|落地|生成).{0,12}计划|计划(?:文档|文件)"
)
PROJECT_SCOPED_PLAN_RE = re.compile(
    r"(?:下|里面|内)(?:的)?\s*(?:一个|一份)?\s*(?<![\w-])plans?(?![\w-])",
    re.IGNORECASE,
)
DRAFT_RE = re.compile(r"\bdrafts?\b|草稿")
SNIPPET_RE = re.compile(r"\bsnippets?\b|片段")
FORUM_RE = re.compile(
    r"\b(?:amt:forum|forum|agent forum)\b|snippet\s*46|\$46",
    re.IGNORECASE,
)
GITLAB_MR_REF_RE = re.compile(r"(?<![\w/])!(\d+)\b")
GITLAB_MR_MENTION_RE = re.compile(r"\bMR\b|\bmerge request\b|合并请求", re.IGNORECASE)
GITLAB_MR_URL_RE = re.compile(
    r"(?P<url>https?://(?P<hostname>[^/]+)/"
    r"(?P<repo>[^?#\s]+?)/-/merge_requests/(?P<iid>\d+)"
    r"(?:[/?#][^\s]*)?)",
    re.IGNORECASE,
)
LLM_COUNCIL_RE = re.compile(r"\bllm-council\b|议会", re.IGNORECASE)
LLM_COUNCIL_INVOKE_RE = re.compile(
    r"(?:按|走|用|执行|启动|召开|发起).{0,8}(?:llm-council|议会)"
    r"|(?:llm-council|议会).{0,8}(?:流程|处理|审议|评审)",
    re.IGNORECASE,
)
LLM_COUNCIL_NON_INVOKE_RE = re.compile(
    r"(?:不要|不用|别|无需|不必).{0,8}(?:llm-council|议会)"
    r"|如果.{0,8}(?:llm-council|议会)",
    re.IGNORECASE,
)
GTD_ENTRYPOINT_RE = re.compile(
    r"\bgtd\b|待办|滴答|开工|MR\s*队列|WorkItem|Meego|个人任务|个人目标"
)
GTD_RUNTIME_RE = re.compile(
    r"\bgtd\s+runtime\b|GTD\s+runtime|本地运行面|挂在\s*runtime|daemon",
    re.IGNORECASE,
)
SAVE_CONTEXT_RECOVER_RE = re.compile(
    r"save-context\s+recover|长线程|卡在压缩|离线恢复|旧\s*Codex\s*线程|interrupted|interrupt",
    re.IGNORECASE,
)

LLM_COUNCIL_ROUTE = {
    "id": "llm-council-workflow",
    "name": "LLM Council deliberation workflow",
    "reference_path": str(HOME / "Documents" / "reference" / "llm-council"),
    "tool_route": "~/.ai/tool-routes.md",
    "tool_route_section": "LLM Council / Deliberation",
    "default_read": ["backend/council.py"],
    "notes": [
        "Use the three-stage council primitive: independent initial answers, anonymous review/ranking, cold-start chairman synthesis.",
        "Do not inherit OpenRouter provider, Web UI, conversation app shell, or a long-running local service by default.",
    ],
}

LLM_COUNCIL_EXECUTION = {
    "required": True,
    "mode": "multi_agent_deliberation",
    "defaults": {
        "initial_agents": 3,
        "reviewer_agents": 1,
        "chairman_agents": 1,
        "artifact_mode": "inline",
    },
    "authorization": {
        "permits": ["read_only_subagents_for_this_deliberation"],
        "does_not_permit": [
            "file_writes",
            "network_or_paid_models",
            "remote_writes",
            "other_scope_expansion",
        ],
    },
    "surface_adapters": {
        "codex": {
            "initial_agent_fork_turns": "none",
            "reviewer_fork_turns": "none",
            "chairman_fork_turns": "none",
        },
    },
    "instructions": [
        "Execute the council in this turn with independent agents; do not simulate multiple personas in one agent response.",
        "Stage 1: compile one self-contained council packet and give that same packet to independent cold-start agents; they must not see each other's answers.",
        "Stage 2: anonymize the initial answers and give only the council question plus anonymous answers to a fresh reviewer for review and ranking.",
        "Stage 3: give the question, anonymous initial answers, and review evidence to a fresh cold-start chairman for final synthesis.",
        "If the current client cannot run independent agents, report that capability boundary instead of pretending the council ran.",
        "Report the actual participant counts and any failed stage; never silently replace missing agents with root-agent roleplay.",
    ],
}

GTD_ENTRYPOINT_ROUTE = {
    "id": "gtd-entrypoint",
    "name": "GTD personal goal domain entrypoint",
    "entrypoint": "~/.ai/scripts/gtd",
    "tool_route": "~/.ai/tool-routes.md#gtd-个人目标域",
    "notes": [
        "Use the GTD aggregate script for personal tasks, todos, calendar/project focus, MR queue, WorkItem handoff, Meego, and TickTick operations.",
        "Do not bypass GTD to edit lower-level personal runtime state directly by default.",
    ],
}

GTD_RUNTIME_ROUTE = {
    "id": "gtd-runtime-daemon",
    "name": "GTD runtime daemon management",
    "entrypoint": "~/.ai/scripts/gtd runtime <list|show|check|restart|run>",
    "tool_route": "~/.ai/tool-routes.md#runtime-daemon-管理",
    "notes": [
        "Use GTD runtime for local daemon and periodic-job management.",
        "Keep runtime daemon work on the GTD runtime entrypoint.",
    ],
}

SAVE_CONTEXT_RECOVER_ROUTE = {
    "id": "save-context-recover",
    "name": "Long Codex thread save-context recovery",
    "entrypoint": "~/.ai/scripts/save-context-recover",
    "tool_route": "~/.ai/tool-routes.md#长线程-save-context-离线恢复",
    "notes": [
        "Use this read-only recovery helper when a long Codex thread is stuck around compaction, interrupted, or blocked before save-context.",
        "The output is evidence for rebuilding context.v2; it is not the final saved context.",
    ],
}

def _norm_path(path: Path) -> str:
    return str(path.expanduser())


def _text_contains_alias(text: str, alias: str) -> bool:
    if re.search(r"[\u3400-\u9fff]", alias):
        return alias.casefold() in text.casefold()
    if re.search(r"[\w:-]", alias):
        return re.search(rf"(?<![\w:-]){re.escape(alias)}(?![\w:-])", text,
                         re.IGNORECASE) is not None
    return alias.lower() in text.lower()


def _route_config_path() -> Path:
    override = os.environ.get("AI_META_ROUTE_CONTEXT_PATH")
    if override:
        return Path(override).expanduser()
    return HOME / ".ai" / "route-context.json"


def _local_route_config_path() -> Path:
    override = os.environ.get("AI_META_ROUTE_CONTEXT_LOCAL_PATH")
    if override:
        return Path(override).expanduser()
    return HOME / ".ai" / "route-context.local.json"


def _read_route_config(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"cannot load {path}: {exc}"
    if not isinstance(config, dict) or config.get("version") != 1:
        return None, f"{path} must be a version 1 JSON object"
    for key in ("path_routes", "special_routes"):
        if not isinstance(config.get(key, []), list):
            return None, f"{path} field {key} must be an array"
    return config, None


def _merged_routes(
    base: dict[str, Any],
    local: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {"version": 1}
    for key in ("path_routes", "special_routes"):
        by_id: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for rule in [*base.get(key, []), *local.get(key, [])]:
            rule_id = rule.get("id") if isinstance(rule, dict) else None
            if not isinstance(rule_id, str) or not rule_id:
                continue
            if rule_id not in by_id:
                order.append(rule_id)
            by_id[rule_id] = rule
        merged[key] = [by_id[rule_id] for rule_id in order]
    return merged


def _load_live_routes() -> tuple[dict[str, Any], Path, str | None]:
    path = _route_config_path()
    empty = {"version": 1, "path_routes": [], "special_routes": []}
    config, error = _read_route_config(path)
    if config is None:
        return empty, path, error

    local_path = _local_route_config_path()
    if not local_path.exists():
        return config, path, None
    local, local_error = _read_route_config(local_path)
    if local is None:
        return empty, path, local_error
    return _merged_routes(config, local), path, None


def _filename_matches(prompt: str, filename: str) -> list[str]:
    pattern = re.compile(
        rf"(?<![\w.-]){re.escape(filename)}(?![\w.-])",
        re.IGNORECASE,
    )
    return [match.group(0) for match in pattern.finditer(prompt)]


def _file_suffix_matches(prompt: str, suffix: str) -> list[str]:
    pattern = re.compile(
        rf"(?<![\w./-])[\w./-]+{re.escape(suffix)}(?![\w.-])",
        re.IGNORECASE,
    )
    return [match.group(0) for match in pattern.finditer(prompt)]


def _host_url_matches(prompt: str, hosts: list[str]) -> list[re.Match[str]]:
    valid_hosts = [host for host in hosts if isinstance(host, str) and host]
    if not valid_hosts:
        return []
    host_pattern = "|".join(re.escape(host) for host in valid_hosts)
    pattern = re.compile(
        rf"(?P<url>https?://(?P<hostname>{host_pattern})"
        rf"(?:/[^\s<>\[\]{{}}\"']*)?)",
        re.IGNORECASE,
    )
    return list(pattern.finditer(prompt))


def _match_live_rule(prompt: str, match_config: Any) -> dict[str, Any]:
    if not isinstance(match_config, dict):
        return {"phrases": [], "urls": [], "mr_iids": []}

    phrases: list[str] = []
    urls = _host_url_matches(prompt, match_config.get("hosts", []))
    phrases.extend(match.group("url") for match in urls)

    for filename in match_config.get("filenames", []):
        if isinstance(filename, str):
            phrases.extend(_filename_matches(prompt, filename))
    for suffix in match_config.get("file_suffixes", []):
        if isinstance(suffix, str) and suffix:
            phrases.extend(_file_suffix_matches(prompt, suffix))
    for keyword in match_config.get("keywords", []):
        if isinstance(keyword, str) and _text_contains_alias(prompt, keyword):
            phrases.append(keyword)

    mr_iids: list[int] = []
    if match_config.get("gitlab_mr_references") is True:
        mr_iids = [int(ref) for ref in GITLAB_MR_REF_RE.findall(prompt)]
        phrases.extend(f"!{iid}" for iid in mr_iids)
        mr_mention = GITLAB_MR_MENTION_RE.search(prompt)
        if mr_mention:
            phrases.append(mr_mention.group(0))

    return {
        "phrases": list(dict.fromkeys(phrases)),
        "urls": urls,
        "mr_iids": mr_iids,
    }


def _apply_live_routes(
    prompt: str,
    config: dict[str, Any],
    resolved_paths: dict[str, Any],
    matches: list[dict[str, str]],
    special_routes: list[dict[str, Any]],
    notes: list[str],
) -> None:
    for rule in config.get("path_routes", []):
        if not isinstance(rule, dict):
            continue
        matched = _match_live_rule(prompt, rule.get("match"))
        if not matched["phrases"]:
            continue
        matches.append({
            "kind": "path_intent",
            "phrase": " ".join(matched["phrases"]),
        })
        for key, value in rule.get("resolved_paths", {}).items():
            if isinstance(key, str) and isinstance(value, str):
                resolved_paths[key] = _norm_path(Path(value))

    for rule in config.get("special_routes", []):
        if not isinstance(rule, dict):
            continue
        matched = _match_live_rule(prompt, rule.get("match"))
        if not matched["phrases"]:
            continue
        route_config = rule.get("route")
        if not isinstance(route_config, dict):
            continue
        matches.append({
            "kind": "special_route",
            "phrase": " ".join(matched["phrases"]),
        })
        route = dict(route_config)
        if isinstance(route.get("notes"), list):
            route["notes"] = list(route["notes"])

        if rule.get("target_parser") == "gitlab_url" and matched["urls"]:
            targets = []
            for url_match in matched["urls"]:
                url = url_match.group("url")
                target = {
                    "url": url,
                    "hostname": url_match.group("hostname").lower(),
                }
                mr_match = GITLAB_MR_URL_RE.fullmatch(url)
                if mr_match:
                    target.update({
                        "repository": mr_match.group("repo"),
                        "mr_iid": int(mr_match.group("iid")),
                    })
                targets.append(target)
            route["targets"] = targets
            if len(targets) == 1:
                route["target"] = targets[0]
        if matched["mr_iids"]:
            route["mr_iids"] = matched["mr_iids"]
        special_routes.append(route)
        if isinstance(rule.get("note"), str):
            notes.append(rule["note"])


def _available_projects() -> dict[str, dict[str, Any]]:
    """Combine built-in routes with project-layer index.md declarations."""
    projects = {
        abbr: dict(project)
        for abbr, project in PROJECTS.items()
        if abbr == "amt" or project["root"].expanduser().exists()
    }
    projects_root = ME_ROOT / "Projects"
    try:
        indexes = sorted(projects_root.glob("*/index.md"))
    except OSError:
        return projects

    for index_path in indexes:
        try:
            lines = index_path.read_text(encoding="utf-8").splitlines()
            header = "\n".join(lines[:30])
        except OSError:
            continue
        match = re.search(r"(?m)^abbr:\s*([^\s#]+)\s*$", header)
        if not match:
            continue

        abbr = match.group(1)
        root = index_path.parent
        existing = projects.get(abbr, {})
        aliases = tuple(dict.fromkeys((
            *(existing.get("aliases") or ()),
            abbr,
            root.name,
        )))
        projects[abbr] = {
            "name": existing.get("name") or root.name,
            "root": root,
            "aliases": aliases,
        }

    return projects


def _project_for_cwd(cwd: Path) -> str | None:
    try:
        resolved = cwd.expanduser().resolve()
    except OSError:
        resolved = cwd.expanduser()

    for abbr, project in _available_projects().items():
        root = project["root"].expanduser()
        try:
            resolved.relative_to(root)
            return abbr
        except ValueError:
            continue
    return None


def _matched_projects(prompt: str, cwd: Path) -> list[dict[str, Any]]:
    matched: dict[str, dict[str, Any]] = {}
    available_projects = _available_projects()

    for abbr, project in available_projects.items():
        phrases = [
            alias for alias in project["aliases"]
            if _text_contains_alias(prompt, alias)
        ]
        if phrases:
            matched[abbr] = {
                "abbr": abbr,
                "name": project["name"],
                "root": _norm_path(project["root"]),
                "matched_phrases": phrases,
                "source": "prompt",
            }

    cwd_abbr = _project_for_cwd(cwd)
    if cwd_abbr and cwd_abbr not in matched:
        project = available_projects[cwd_abbr]
        matched[cwd_abbr] = {
            "abbr": cwd_abbr,
            "name": project["name"],
            "root": _norm_path(project["root"]),
            "matched_phrases": [],
            "source": "cwd",
        }

    return list(matched.values())


def _primary_project(projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    explicit = [project for project in projects if project["source"] == "prompt"]
    if explicit:
        return explicit[0]
    if projects:
        return projects[0]
    return None


def resolve_route_context(prompt: str, cwd: str | Path) -> dict[str, Any]:
    cwd_path = Path(cwd).expanduser()
    projects = _matched_projects(prompt, cwd_path)
    primary_project = _primary_project(projects)
    resolved_paths: dict[str, Any] = {}
    matches: list[dict[str, str]] = []
    notes: list[str] = []
    special_routes: list[dict[str, Any]] = []
    live_routes, live_routes_path, live_routes_error = _load_live_routes()
    if live_routes_error:
        notes.append(f"route-context live config unavailable: {live_routes_error}")
    else:
        _apply_live_routes(
            prompt,
            live_routes,
            resolved_paths,
            matches,
            special_routes,
            notes,
        )

    if DRAFT_RE.search(prompt):
        matches.append({"kind": "path_intent", "phrase": "draft"})
        resolved_paths["draft"] = _norm_path(DRAFT_DIR)

    forum_match = FORUM_RE.search(prompt)
    if forum_match:
        matches.append({"kind": "special_route", "phrase": forum_match.group(0)})
        special_routes.append(FORUM_SNIPPET_46)
        notes.append(
            "forum/snippet 46 resolves to the GitLab project snippet source of truth, not the local Snippets directory."
        )

    if SNIPPET_RE.search(prompt):
        matches.append({"kind": "path_intent", "phrase": "snippet"})
        if not forum_match:
            resolved_paths["snippet"] = _norm_path(SNIPPETS_DIR)

    llm_council_match = LLM_COUNCIL_RE.search(prompt)
    if llm_council_match:
        matches.append({
            "kind": "special_route",
            "phrase": llm_council_match.group(0),
        })
        route = dict(LLM_COUNCIL_ROUTE)
        if (LLM_COUNCIL_INVOKE_RE.search(prompt)
                and not LLM_COUNCIL_NON_INVOKE_RE.search(prompt)):
            route["execution"] = LLM_COUNCIL_EXECUTION
        special_routes.append(route)
        notes.append(
            "llm-council/议会 resolves to the LLM Council deliberation workflow in tool-routes, not a generic meeting or discussion."
        )

    gtd_runtime_match = GTD_RUNTIME_RE.search(prompt)
    if gtd_runtime_match:
        matches.append({
            "kind": "special_route",
            "phrase": gtd_runtime_match.group(0),
        })
        special_routes.append(GTD_RUNTIME_ROUTE)
        notes.append(
            "GTD runtime/local daemon wording resolves to ~/.ai/scripts/gtd runtime."
        )

    save_context_recover_match = SAVE_CONTEXT_RECOVER_RE.search(prompt)
    if save_context_recover_match:
        matches.append({
            "kind": "special_route",
            "phrase": save_context_recover_match.group(0),
        })
        special_routes.append(SAVE_CONTEXT_RECOVER_ROUTE)
        notes.append(
            "Long/interrupted Codex thread recovery resolves to the read-only save-context-recover helper."
        )

    gtd_entrypoint_match = GTD_ENTRYPOINT_RE.search(prompt)
    if gtd_entrypoint_match:
        matches.append({
            "kind": "special_route",
            "phrase": gtd_entrypoint_match.group(0),
        })
        special_routes.append(GTD_ENTRYPOINT_ROUTE)
        notes.append(
            "GTD/personal goal domain wording resolves to the aggregate ~/.ai/scripts/gtd entrypoint."
        )

    durable_doc_requested = bool(
        EN_DURABLE_DOC_RE.search(prompt)
        or any(term in prompt for term in ZH_DURABLE_DOC_TERMS)
    )

    plan_mentioned = bool(PLAN_RE.search(prompt) or ZH_PLAN_ARTIFACT_RE.search(prompt))
    explicit_project = bool(
        primary_project and primary_project.get("source") == "prompt"
    )
    plan_artifact_requested = bool(
        DOCS_PLAN_RE.search(prompt)
        or EN_PLAN_ARTIFACT_RE.search(prompt)
        or ZH_PLAN_ARTIFACT_RE.search(prompt)
        or (explicit_project and PROJECT_SCOPED_PLAN_RE.search(prompt))
    )

    if plan_mentioned and plan_artifact_requested:
        matches.append({"kind": "path_intent", "phrase": "plan"})
        if durable_doc_requested:
            notes.append(
                "plan was mentioned with durable docs/ADR/runbook/architecture wording; do not default it to docs/plan."
            )
        elif primary_project:
            plan_path = str(Path(primary_project["root"]) / "docs" / "plan")
            resolved_paths["plan"] = plan_path
            notes.append(
                f"{plan_path} is the deterministic target for this project-layer plan request. "
                "Use it instead of a source-repository-local work-plan location such as .local/plans; "
                "repo-local plan conventions apply only when the user explicitly requests a repo-local plan."
            )
        else:
            notes.append(
                "plan defaults to <project_root>/docs/plan only after a project is resolved."
            )

    return {
        "schema": "route_context.v0",
        "cwd": str(cwd_path),
        "route_config": {
            "path": str(live_routes_path),
            "loaded": live_routes_error is None,
            "error": live_routes_error,
        },
        "projects": projects,
        "primary_project": primary_project,
        "matches": matches,
        "resolved_paths": resolved_paths,
        "special_routes": special_routes,
        "notes": notes,
    }


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve user shorthand into route-context JSON.")
    parser.add_argument("--prompt", help="User prompt. Defaults to stdin.")
    parser.add_argument("--cwd", default=str(Path.cwd()),
                        help="Current working directory for fallback project resolution.")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    result = resolve_route_context(_read_prompt(args), args.cwd)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
