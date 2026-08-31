---
name: review-router
description: Route independent code-change reviews through simple, challenge, two-axis, quality, prune, or evolution strategies. Use for rr, fresh review requests over code/diffs/branches/MRs/PRs/evidence, deletion or simplification review, and engineering read-only review gates. Do not use merely to triage or answer existing reviewer feedback.
---

# review-router

Fix the target, select one strategy, and return findings, verdict, and one next-review decision. review-router is read-only: it never fixes, deletes, writes Git/remote state, owns release gates, or persists state.

Use `review-router` in prose and results; reserve `rr` and `rr ...` for user invocation.

## Baseline

Resolve target/baseline, acceptance/spec, project standards, full relevant diff/context, and verification evidence before asking. Evolution also requires caller-owned revision, fingerprint, round, and prior findings.

Stop for an unresolved baseline or empty diff. Bind MR/PR review to its actual head revision; never use `HEAD~1` or one commit as the full change.

## Selection

- Explicit strategy wins.
- Refactor, architecture governance, KISS/DRY, file splitting, or code health → `quality` over the complete diff.
- Deletion, YAGNI, dependency reduction, native/stdlib replacement, over-engineering, or rejected-scope residue → `prune`; broader architecture/security/performance uncertainty → `quality`.
- `rr simple` → simple only. Plain `rr`/`rr auto` → simple, then at most its one recommended strategy.
- `caller=engineering-exit` → simple plus at most one evidence-backed escalation; caller owns disposition.
- `rr challenge|two-axis|quality|prune|evolution` → only that strategy.

Choose the one next strategy most likely to change readiness. Diff size or checklist availability is not evidence for escalation.

## Strategy Routes

- **Simple**: read `references/simple-review.md` for the default maintainer pass and next-strategy decision.
- **Challenge**: read `references/challenge-review.md` to challenge real-consumer proof, not ordinary code quality.
- **Evolution**: read `references/evolution-review.md` only with caller-owned revision/round state.
- **Two-axis**: use `~/Documents/reference/matt-skills/skills/engineering/code-review/SKILL.md`; fix baseline and report independent Spec and Standards passes.
- **Quality**: use `~/Documents/reference/addy-agent-skills/skills/code-review-and-quality/SKILL.md`; read only `The Five-Axis Review`, `Review Process`, and `Verification`, then select material axes.
- **Prune**: use `~/Documents/reference/ponytail/skills/ponytail-review/SKILL.md`; tag cuts `delete|stdlib|native|yagni|shrink`, identify replacements, sort by reduction, and end with `net: -<N> lines possible.` or `Lean already. Ship.` Remove rejected-scope residue unless independent safety, compatibility, or contract evidence requires it. Never label accessibility, data-loss prevention, or a minimal runnable check as bloat.

External lenses are direct and narrow; do not inherit tracker/client workflow. If missing, apply the local bullet contract without searching or installing substitutes.

## Evidence

For mixed observation, computation, inference, framework assumptions, or guesses, read `../engineering-exit/references/evidence-classification.md`. Only direct/computed evidence proves a claim; support inference and keep framework claims conditional.

## Results And Boundaries

- Preserve each strategy's verdict, vocabulary, and required sections; do not flatten challenge/evolution into simple.
- Findings come first at the narrowest file/line/evidence anchor with impact and correction/decision. Say `no material findings` instead of inventing one.
- End with `next_review.strategy: none|two-axis|quality|prune|challenge`, one evidence-backed reason, and an unresolved question unless `none`.
- Do not append inventories, tool narration, or generic walkthroughs.
- A recommendation never authorizes fixes or scope expansion. Domain architecture, UI, release, and security gates remain with their owners.
