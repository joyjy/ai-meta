---
name: agent-doc-hygiene
description: 专门巡检并收敛 agent-facing 文档，让 agent 加载路径短、上下文内有效、规则单一且可执行。Use when the user asks for agent 文档治理、文档瘦身、记忆优化、精简 agent 文档、清理 context/memory，或 engineering-exit 需要对当前 diff 执行 bounded agent-facing docs gate。
---

# agent-doc-hygiene

Audit agent-facing docs by loading behavior. Keep hot entries short and rules singly owned without losing safety or recoverability.

Default to review-only. Edit, commit, or push only with explicit authorization.

## Scope

Resolve one mode before listing files:

- `global`: inspect cross-project instructions, routes, reusable skills, commands, conventions, and context protocols; do not scan every project.
- `project`: inspect the named/current project's agent loading path and related context.
- `project + exit-gate`: inspect only touched agent docs and directly implicated loading paths; route broader findings to follow-up.

Enumerate Markdown with `rg --files -g '*.md'`, covering root and `src/` skill/agent/command layouts. Track read files as evidence and skipped candidates as uncovered; never call uncovered files clean.

Read `references/layer-rules.md` only for project entries, README, source maps, durable/doc-root layers, context/memory, backlog, changelog, or history. Do not load it for a skill/command-only audit.

## Loading-Path Gates

- Read every in-scope main `SKILL.md` completely, even when only one line changed.
- Record `entry_bytes`, `default_references`, conditional references with triggers, `default_transitive_bytes = entry_bytes + unconditional reference bytes`, and `max_reference_depth`.
- More than 4 KB is at least `Watch`; more than 6 KB is `Must Fix` unless routing would hide an invocation or safety decision.
- An unconditional broad reference, a default path that does not become smaller, or a reference chain deeper than one level is `Must Fix`.
- Keep invocation, safety, default path, and routing in the main skill. Move conditional procedures, checklists, examples, rationale, and history to direct references or their owner.
- Prefer a short duplicated safety gate only when it must be visible before tool use. Otherwise one rule has one owner and other files use a pointer or brief summary.
- Treat an agent-facing rule, comment, or explanation whose only purpose is to describe a user-rejected or removed addition as residue, not rationale. Remove it so the final loading path reads as if that addition never existed; retain text only when independent current evidence proves a real safety, compatibility, or external-contract boundary.

Size triggers inspection, not deletion. Prove compressed content has a better owner or move it first.

## Behavioral Gates

Check effects on the task, not just document size:

- Authority: distinguish source material from instructions; find defaults that override an explicit request, invent permission, or repeat an already-satisfied approval gate. Preserve platform hierarchy and real safety boundaries.
- Triggers and stops: find unconditional questions, output templates, delegation, verification expansion, or terminal polling where the task needs a conditional choice. Require a clear trigger and completion boundary, not a universal ban.
- Host overlap: compare with visible platform guidance; remove conflicting or redundant local rules only when the host covers the same need. Retain necessary cross-client rules; unknown host behavior is not evidence of duplication.

Use the finding buckets below and keep fixes model-independent; do not copy a model guide into the skill.

## Workflow

1. State mode, target root, candidate scope, evidence set, and uncovered set.
2. Measure each in-scope main skill and map its ordinary loading closure.
3. Diagnose placement, weight, duplication, staleness, loading breadth, and behavioral gates.
4. Classify findings:
   - `Must Fix`: repeated or clearly impactful friction with a small durable fix, plus every hard loading-path violation above.
   - `Watch`: plausible risk or one recent correction without enough evidence for a rule change.
   - `Do Not Change`: cleanup that would overfit, duplicate a source of truth, or add more weight than it removes.
5. Plan only `Must Fix`. When authorized, slim hot entries, deduplicate, then move conditional detail.
6. Verify searchability, paths/links, source-of-truth pointers, loading closure/depth, and preserved recovery state. For changed behavioral rules, compare before/after decisions on a few relevant real requests (e.g. explicit edit, discussion only, context load), including action/read scope and stopping point. Label a static walkthrough as such; fewer bytes or a walkthrough alone does not prove runtime improvement. Do not build a test framework just for wording changes.
7. Report files changed, content moved and intentionally retained, all three finding buckets, every reviewed skill's five loading metrics, behavioral evidence and its limits, evidence set, and uncovered set.

## Boundaries

- Keep scope narrow; expand only to owners needed to resolve duplication or routing.
- Do not turn product or architecture docs into primary slimming targets; use `doc-arch-review` for semantic architecture or source-map accuracy.
- Do not upgrade project preferences into global rules without repeated cross-project evidence.
- Do not delete unfinished work, blockers, decisions, or history without a clear destination and required approval.
- If context capacity prevents a reliable audit, report the exact completed and uncovered scope and offer `save-context`; do not interrupt useful authorized work merely because the inventory is large.
