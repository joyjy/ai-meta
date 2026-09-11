---
name: review-router
description: Route rr code/MR/PR, module, whole-repository, simplification and explicit design reviews. Excludes ordinary document requests and feedback triage.
---

# review-router

Fix scope and identity before strategy. Return findings, verdict and one next-review decision. Read-only: no fixes, deletion, Git/remote writes, release gates or persisted state. Use `review-router` in prose; `rr` is a user alias.

## Scope Before Strategy

Infer the intended decision from the request and conversation, not the latest commit or convenient dirty diff. Explicit scope wins. Briefly state scope, target and comparison baseline (or current snapshot).

| Scope | Intent | Boundary |
| --- | --- | --- |
| Incremental re-review | “刚修的再看下”, “这些反馈解决了吗” | Changes since the identified reviewed revision, unresolved findings and affected consumers. Resolve a missing baseline; never substitute `HEAD~1` silently. |
| Complete delivery | “这个 MR / 任务能交了吗”, “最后收口” | All task-owned commits and dirty changes against the delivery baseline, with consumers and integration evidence. Bind MR/PR to actual base/head; distinguish unpublished local follow-up. |
| Existing module | “这个模块是不是太复杂”, named subsystem review | Current implementation, responsibilities, dependencies, compatibility and relevant callers beyond the module. No diff required. |
| Whole repository | “全仓扫一下”, “给项目做个体检” | The identified repository's current code, docs, dependencies/build configuration and validation entrypoints. No diff required; never silently narrow to recent changes or one module. |

Follow concrete contract/consumer impacts beyond incremental hunks. Neither incremental nor complete-delivery review implies a repository audit.

For module/repository scans, map structure and owners, then deepen by risk. Account for each top-level repository area as inspected, sampled or excluded with a reason; trace generated/vendor artifacts to their source owner. Separate existing debt from delivery-introduced issues. Sampling cannot prove exhaustive correctness; empty diffs do not stop snapshot reviews.

Resolve facts before asking; ask only when remaining ambiguity changes the review scope. An empty change diff has no new code, but unresolved findings still need disposition; do not switch to a repository scan. Use a single commit or `HEAD~1` only when user-selected.

## Baseline

Bind acceptance/spec, standards, selected diff/snapshot, relevant context and verification evidence. Evolution additionally requires caller-owned revision, fingerprint, round and prior findings.

For explicit `design`, bind the file/section/proposal, problem, constraints, current anchors and decision question. No diff required. Verify rationale against reality; missing decisions can warrant `not-ready`.

## Strategy Selection

- Explicit strategy wins; run only that strategy, including `simple` or `design`.
- Plain `rr` / `rr auto` never infer design from Markdown or a proposal.
- Refactor, architecture governance, KISS/DRY, splitting or code health → `quality` over the selected scope and structural context.
- Deletion, YAGNI, native/stdlib replacement or over-engineering → `prune`; broader architecture/security/performance risk → `quality`.
- Otherwise plain `rr` / `rr auto`, and `caller=engineering-exit` → simple plus at most one evidence-backed escalation; caller owns disposition.

Choose `none` when no material question remains. Size or checklist availability alone never justifies escalation.

## Strategy Routes

- **Simple**: `references/simple-review.md` — maintainer pass and next-strategy decision.
- **Design**: `references/design-review.md` — explicit proposal semantics and feasibility.
- **Challenge**: `references/challenge-review.md` — real-consumer proof.
- **Evolution**: `references/evolution-review.md` — requires caller-owned round state.
- **Two-axis**: `~/Documents/reference/matt-skills/skills/engineering/code-review/SKILL.md` — bind baseline; independent Spec and Standards passes.
- **Quality**: `~/Documents/reference/addy-agent-skills/skills/code-review-and-quality/SKILL.md` — read only `The Five-Axis Review`, `Review Process`, `Verification`; select material axes.
- **Prune**: `~/Documents/reference/ponytail/skills/ponytail-review/SKILL.md` — tag `delete|stdlib|native|yagni|shrink`, identify replacements, sort by reduction; end `net: -<N> lines possible.` or `Lean already. Ship.` Flag rejected-scope residue unless real safety, compatibility or contract evidence requires it. Accessibility, data-loss prevention and a minimal runnable check are not bloat.

External lenses are direct and narrow; do not inherit tracker/client workflows. If absent, use the bullet contract above without searching or installing substitutes.

## Evidence And Results

- For mixed observations, calculations, inference or framework assumptions, read `../engineering-exit/references/evidence-classification.md`. Only direct/computed evidence proves claims; support inference and qualify framework claims.
- Preserve the strategy's verdict, vocabulary and required sections; do not flatten it into simple.
- Findings first, at the narrowest file/line or artifact/evidence anchor, with impact and correction/decision. Say `no material findings` when appropriate.
- Report actual coverage and omissions, including area accounting for snapshot scans. Avoid raw file inventories or tool narration; a pass applies only to stated coverage.
- End with `next_review.strategy: none|two-axis|quality|prune|challenge`, an evidence-backed reason and an unresolved question unless `none`.
- Review recommendations grant no fix or scope-expansion authority. Domain/release/security gates remain with their owners.
- Design stays one-shot/read-only; it does not replace doc-arch-review's durable-document ownership review or become grill/steelman.
