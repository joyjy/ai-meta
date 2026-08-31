---
name: load-context
description: "Restore a saved project or workstream context from ~/.ai/contexts. Triggered by load context, 加载上下文, 恢复 session, /load-context, or an abbr like amt or amt:workstream."
disable-model-invocation: true
---

# load-context

Restore a saved project or workstream recovery snapshot. This skill is the source of truth; command files are thin entrypoints.

## Route Resolution

Resolve in order:

1. Explicit `<abbr>` or `<abbr>:<workstream>`.
2. Current project `index.md` frontmatter `abbr:`.
3. Search project `index.md` files for exactly one entry covering the current repo. Prefer: project directory contains cwd; Source/Links names cwd; Source/Links names git remote; Source/Links names repo basename; project basename matches repo basename. Verify the abbr against `~/.ai/contexts/<abbr>.md` when repo hints exist.
4. If unknown or tied, ask for abbr and stop.

Never infer abbr from context filenames, fuzzy matches, generated acronyms, or code-only directories without project `index.md`. When fallback resolves it, report the supplying `index.md` and whether context verification matched.

A bare `<abbr>` explicitly selects the project mainline. Load a workstream only when the user names `<abbr>:<workstream>`; never auto-select `next_route`, the only active workstream, or any other context metadata. The user's explicit route always wins over stored routing hints.

## Paths And Read Boundary

- Project context: `~/.ai/contexts/<abbr>.md`; context.v2 embeds all workstreams.
- Legacy `~/.ai/contexts/<abbr>/<workstream>.md` is fallback only when v2 lacks the requested workstream.
- A standard context starts with YAML frontmatter; its second line is a compact route-index comment. YAML owns goal/status/summaries; Markdown holds selected-route recovery detail.
- Structured Next Steps are recovery notes, never current-turn authorization, routing, or execution policy. Hide machine-only fields from the human summary.
- Load only the resolved `index.md`, target context, selected route, and minimal probes below. Do not expand templates, docs, ADRs, source, or referenced files unless requested or one small file is required to understand the snapshot.
- Durable facts override conflicting context, but open their owner only when needed for the user's next task.

## Conditional Health Branch

Read `references/health-check.md` only when the user asks for context/project health, or when loading observes a malformed/oversized context, missing or mismatched project/source root, stale health warning, entry-file anomaly, or unresolved GitLab metadata that affects the selected repo. Ordinary load does not run project-wide line counts or GitLab lint.

Health findings are advisory: they never authorize stored Next Steps, file edits, cleanup, lint remediation, or event settlement, and block loading only when the target context is missing or unreadable.

## Workflow

1. Resolve route. Read `~/.ai/contexts/<abbr>.md`; for a bare `<abbr>`, select mainline even when YAML recommends a workstream through `next_route`. For explicit `<abbr>:<workstream>`, select the named workstream when present, otherwise use the legacy fallback. If the project context is missing, say `~/.ai/contexts/<abbr>.md 不存在，请先运行 /save-context <abbr>`. If a workstream is absent from both locations, report the exact missing route and ask the user to confirm its name or load mainline.
2. Read the route index and YAML, then only the selected Markdown section. Expand further only when Goal/Doing/Blocked/Next Steps/Critical Context are not visible. Mainline may list workstream summaries without loading their detail.
3. Internalize Goal, unfinished Doing, Blocked, first Next Step, and critical anchors as background only. Do not execute or ask whether to continue; wait for the user's next request.
4. Run count-only `~/.ai/scripts/agent-frictions status --owner context:<abbr>:<selected-route>`. Do not load, interpret, or settle events; only surface nonzero `actionable_count`.
5. Run the conditional health branch only when triggered. Do not investigate unrelated files from a health finding.
6. Return the compact human summary below.

## Output

```markdown
已加载 context: <abbr> / <abbr>:<workstream>

目标：<Goal 一句话>

当前状态：无

下一步：<第一条；无则写 无>

阻塞问题：<仅 context 明确记录时>
活跃分线：<仅主线且存在时>
临时文件：<仅 context 记录 stale exact paths 时>
健康提示：<仅触发 health branch 且有问题时，最多 1-3 条>
摩擦候选：<仅 actionable_count > 0 时写 N 条待下次 save-context 结算>
```

Keep it short and mention fallback resolution when used. With no concrete next step, write exactly `下一步：无` and add no fallback suggestion. When Doing and Blocked are both empty, use `当前状态：无`; otherwise list only populated `Doing`/`Blocked` items. Do not use variants such as “无硬 blocker”.
