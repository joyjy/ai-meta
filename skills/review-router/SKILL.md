---
name: review-router
description: Route independent code-change reviews through simple, challenge, two-axis, quality, prune, or evolution strategies. Use when the user says rr, asks Codex to review code, a diff, branch, MR/PR, implementation, or verification evidence, asks what can be deleted or simplified, or when an engineering workflow needs a read-only review gate and a decision about whether deeper review is warranted. Do not use merely to read, triage, or respond to feedback already left by another reviewer unless the user explicitly asks for a fresh independent review.
---

# review-router

Fix the review target, select one strategy, and return findings, verdict, and one next-review decision. review-router is read-only: it never fixes, deletes, writes Git/remote state, owns release gates, or persists workflow state.

Use `review-router` in prose and results; reserve `rr` and `rr ...` for user invocation.

## Baseline

Resolve target/baseline, goal/acceptance/spec, project standards, full relevant diff/context, and verification evidence from the repo/session before asking. Evolution additionally requires caller-owned revision, fingerprint, round, and prior findings.

Stop for an unresolved baseline or empty diff. Bind MR/PR review to its actual head revision; never use `HEAD~1` or one commit as the full change.

## Selection

- Explicit strategy wins.
- Refactor, architecture governance, KISS/DRY, large-file split, or code health → `quality` over the complete diff.
- Deletion, YAGNI, dependency reduction, native/stdlib replacement, over-engineering, or residue from a user-rejected scope addition → `prune`; broader architecture/security/performance uncertainty → `quality`.
- `rr simple` → simple only. Plain `rr`/`rr auto` → simple, then at most its one recommended strategy.
- `caller=engineering-exit` → simple plus at most one evidence-backed read-only escalation; caller owns disposition.
- `rr challenge|two-axis|quality|prune|evolution` → only that strategy.

Choose the one next strategy most likely to change readiness. Diff size or checklist availability is not evidence for escalation.

## Strategy Routes

- **Simple**: read `references/simple-review.md` for the default maintainer pass and next-strategy decision.
- **Challenge**: read `references/challenge-review.md` to challenge real-consumer proof, not ordinary code quality.
- **Evolution**: read `references/evolution-review.md` only with caller-owned revision/round state.
- **Two-axis**: directly use `~/Documents/reference/matt-skills/skills/engineering/code-review/SKILL.md` as a narrow lens. Fix baseline and run independent Spec and Standards passes; report them separately.
- **Quality**: directly use `~/Documents/reference/addy-agent-skills/skills/code-review-and-quality/SKILL.md`, reading only `The Five-Axis Review`, `Review Process`, and `Verification`. Select material correctness, simplicity, architecture, security, and performance axes; do not manufacture checklist findings.
- **Prune**: directly use `~/Documents/reference/ponytail/skills/ponytail-review/SKILL.md`. Tag located cuts `delete|stdlib|native|yagni|shrink`, identify replacements, sort by net reduction, and end with `net: -<N> lines possible.` or `Lean already. Ship.` Treat comments, docs, tests, config, changelog, or MR text whose only purpose is to explain a user-rejected or removed addition as `delete`: the reviewed result should read as if that addition never existed. Retain only independently evidenced current safety, compatibility, or external-contract constraints. Never treat safety, accessibility, data-loss prevention, or a minimal runnable check as bloat.

External lenses are direct and narrow; do not inherit tracker/client workflow. If missing, apply the local bullet contract without searching or installing substitutes.

## Evidence

When a material conclusion mixes observation, computation, inference, framework assumptions, or guesses, directly read `../engineering-exit/references/evidence-classification.md`. Only direct/computed evidence proves it; show inference support, keep framework claims conditional, and never base a finding on guess alone. Use review-router's user-facing `evidence`, `agent proved`, `agent did not prove`, and `human verification` language.

## Results And Boundaries

- Each strategy owns its verdict and finding vocabulary. Preserve its required sections; do not flatten challenge/evolution into the simple schema.
- Findings come first, attach to the narrowest file/line/evidence anchor, and state impact plus required correction/decision. Say `no material findings` instead of inventing one.
- End with `next_review.strategy: none|two-axis|quality|prune|challenge`, one evidence-backed reason, and an unresolved question unless `none`.
- Do not append inventories, tool narration, or generic walkthroughs.
- A recommendation never authorizes fixes or scope expansion. Domain architecture, UI, release, and security gates remain with their owners.
