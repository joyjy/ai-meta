---
name: agent-doc-hygiene
description: 巡检 agent 文档、skill 与 context 的加载路径和规则效果；用于规则归属、外部 skill 机制吸收、文档瘦身、记忆清理及 engineering-exit 文档门禁。
---

# agent-doc-hygiene

Audit agent-facing docs by loading behavior. Keep hot entries short and rules singly owned without losing safety or recoverability.

Default to review-only. Edit, commit, or push only with explicit authorization.

## Scope

Resolve one mode before listing files:

- `global`: inspect cross-project instructions, routes, reusable skills, commands, conventions, and context protocols; do not scan every project.
- `project`: inspect the named/current project's agent loading path and related context.
- `project + exit-gate`: inspect only touched agent docs and directly implicated loading paths; route broader findings to follow-up.

When the target is already exact, inspect it and directly implicated loading paths. When discovery is needed, use `rg --files -g '*.md'` within the selected scope, including relevant root and `src/` layouts. Track inspected files and relevant skipped candidates; never call skipped files clean.

Read `references/layer-rules.md` only for project entries, README, source maps, durable/doc-root layers, context/memory, backlog, changelog, or history. Do not load it for a skill/command-only audit.

## Placement Before Recommendation

Before recommending where a rule or external pattern belongs, state the observed behavior gap and its trigger without naming a destination. Inspect the applicable owner and existing coverage; distinguish the owner that decides from a consumer that only executes or records the decision. Use a bounded search of responsibilities, not the most recently discussed or edited artifact. Check whether the same owner would follow from the evidence without that recent conversational cue. If current mechanisms already cover the need, choose `Do Not Change`; if the rule exists but was missed, repair its discovery or decision gate rather than adding another copy. An unresolved owner stays unresolved; do not create a new skill just to give the pattern a home.

## Loading-Path Gates

- Read every in-scope main `SKILL.md` completely, even when only one line changed.
- Record `entry_bytes`, `default_references`, conditional references with triggers, `default_transitive_bytes = entry_bytes + unconditional reference bytes`, and `max_reference_depth`.
- More than 4 KB is `Watch`; above 6 KB prioritize checking the actual default loading path and duplication. Size alone never makes a `Must Fix`.
- Trace unconditional broad references, unchanged default loading, and chains deeper than one level. Mark `Must Fix` when they add irrelevant context, hide an invocation or safety decision, or misroute work; otherwise keep them under `Watch`.
- Keep invocation, safety, default path, and routing in the main skill. Move conditional procedures, checklists, examples, rationale, and history to direct references or their owner.
- Prefer a short duplicated safety gate only when it must be visible before tool use. Otherwise one rule has one owner and other files use a pointer or brief summary.
- Treat an agent-facing rule, comment, or explanation whose only purpose is to describe a user-rejected or removed addition as residue, not rationale. Remove it so the final loading path reads as if that addition never existed; retain text only when independent current evidence proves a real safety, compatibility, or external-contract boundary.

Size triggers inspection, not deletion. Prove compressed content has a better owner or move it first.

## Behavioral Gates

Check effects on the task, not just document size:

- Authority: distinguish source material from instructions; find defaults that override an explicit request, invent permission, or repeat an already-satisfied approval gate. Preserve platform hierarchy and real safety boundaries.
- Conflicts: inspect rules loaded at a failed choice or expected to apply together in a concrete scenario; do not require a prior failure. Compare their required actions, authority, scope and owner, including user corrections. Report the shared trigger and incompatible actions; if hierarchy or explicit precedence resolves them, record that resolution rather than an unresolved conflict. Distinguish missing facts, superseded rules, overbroad conditions and unresolved policy decisions. Keep discovery within the selected scope and directly implicated loading paths, not all rule pairs. Follow global instructions for the current action; do not default to the strictest rule or turn instance approval into standing authority. A memory correction alone does not repair a conflicting execution rule.
- Triggers and stops: find unconditional questions, output templates, delegation, verification expansion, or terminal polling where the task needs a conditional choice. Require a clear trigger and completion boundary, not a universal ban.
- Host overlap: compare with visible platform guidance; remove conflicting or redundant local rules only when the host covers the same need. Retain necessary cross-client rules; unknown host behavior is not evidence of duplication.

Use the finding buckets below and keep fixes model-independent; do not copy a model guide into the skill.

## Workflow

1. State mode, target root, candidate scope, evidence set, and uncovered set.
2. Measure each in-scope main skill and map its ordinary loading closure.
3. Apply Placement Before Recommendation, then diagnose weight, duplication, staleness, loading breadth, and behavioral gates.
4. Classify findings:
   - `Must Fix`: demonstrated loading waste, conflicting or missing ownership, safety or authority misrouting, or repeated behavior friction with a small durable fix.
   - `Watch`: plausible risk or one recent correction without enough evidence for a rule change.
   - `Do Not Change`: cleanup that would overfit, duplicate a source of truth, or add more weight than it removes.
5. Prioritize `Must Fix`; address `Watch` when the user explicitly requests it or new evidence makes it actionable. Repair authorized findings at their canonical owner by replacing stale text or narrowing its condition, then check directly affected consumers; do not add a competing rule or stop at a proposal when the repair is authorized. Otherwise return the exact owner, proposed change and remaining decision. Keep the task outcome separate from the rule repair.
6. Verify searchability, paths/links, source-of-truth pointers, loading closure/depth, and preserved recovery state. For changed behavioral rules, compare before/after decisions on representative requests, including a case that can proceed under existing authority and one that must retain a checkpoint. Label historical replay or static walkthrough as such. Record implementation separately from post-load behavior; revisit through the existing review only when evidence or disposition changes. Fewer bytes or a walkthrough does not prove runtime improvement. Do not build a test framework just for wording changes.
7. Report material findings, changed files, content moved or retained, each reviewed skill's five loading metrics, behavioral evidence and its limits, inspected files, and relevant uncovered scope. Name empty finding buckets only when they explain the decision.

## Boundaries

- Keep scope narrow; expand only to owners needed to resolve duplication or routing.
- Do not turn product or architecture docs into primary slimming targets; use `doc-arch-review` for semantic architecture or source-map accuracy.
- Do not upgrade project preferences into global rules without repeated cross-project evidence.
- Do not delete unfinished work, blockers, decisions, or history without a clear destination and required approval.
- If context capacity prevents a reliable audit, report the exact completed and uncovered scope and offer `save-context`; do not interrupt useful authorized work merely because the inventory is large.
