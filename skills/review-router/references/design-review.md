# Design Review

Review the semantic quality of one explicitly selected plan, spec, solution proposal, architecture design, or decision set. The target may be a file or an explicit conversational artifact. Judge whether the solution should guide implementation; do not copy-edit it, rewrite it, or require a document template.

## Baseline

Fix the target, driving problem or outcome, acceptance or decision question, material constraints, current-state anchors, and available evidence. Separate recorded facts, assumptions, decisions, and rationale. Missing context is a finding only when it can change the decision or force an implementer to invent behavior; do not demand ceremonial sections or exhaustive alternatives.

## Review Axes

- **Problem fit**: the proposal solves the stated problem at the right scope and does not substitute a convenient implementation for the actual outcome.
- **Constraints and evidence**: load-bearing requirements, current-system facts, external contracts, assumptions, and technology claims are explicit and supported strongly enough for the decision.
- **Alternatives and trade-offs**: material alternatives were considered when a real choice exists; the chosen trade-off, rejected scope, and revisit condition are visible enough to avoid accidental reversal.
- **Boundaries and behavior**: ownership, authority, source of truth, dependency direction, shared state, lifecycle, failure modes, permissions, and compatibility are closed wherever the proposal crosses those boundaries.
- **Simplicity and reversibility**: complexity earns its cost; speculative abstraction or compatibility is absent; migration, rollback, lock-in, and recovery match the blast radius.
- **Implementability and proof**: downstream implementers can proceed without inventing unrecorded decisions, and acceptance, verification, rollout, health/readback, and terminal evidence can prove the intended outcome where they materially apply.

Apply only material axes. A local module proposal need not discuss deployment; a stateful distributed design cannot omit its failure and authority model.

## Method

1. Reconstruct the proposal's claims and constraints without strengthening them from unstated context.
2. Trace each load-bearing decision to its consumers and operational consequences. Try to construct two implementations that obey the proposal yet behave incompatibly; any material divergence is a gap.
3. Challenge rationale separately from evidence. A plausible explanation does not prove feasibility, compatibility, or current technology behavior.
4. Prefer the smallest correction that closes the decision gap. Do not turn preferences, optional polish, or hypothetical future scale into findings.

## Severity And Verdict

- `P0`: the design permits a dangerous, irreversible, or authority-conflicting outcome without a guard.
- `P1`: a contradiction, missing load-bearing decision, unsupported feasibility claim, or unclosed boundary makes implementation unsafe or forces material invention.
- `P2`: the design remains implementable, but a concrete trade-off, evidence gap, migration risk, or verification weakness should be resolved or explicitly accepted.

Verdict:

- `ready`: no material findings.
- `ready-with-concerns`: only P2 findings remain.
- `not-ready`: any P0/P1 finding remains, or downstream work requires inventing a material decision.

## Result

Return `strategy: design`, then severity-ordered findings with the narrowest artifact section or claim, evidence, consequence, and required decision or correction. If clean, say `no material findings`. Return `verdict: ready|ready-with-concerns|not-ready`.

End with `next_review.strategy: challenge|none` and one evidence-backed reason plus the exact unresolved question unless `none`. Choose `challenge` only when corresponding implementation and verification evidence already exist, but readiness still depends on a real-consumer, runtime, permissions, deployment, lifecycle, or operational proof gap. When implementation does not yet exist, keep `next_review.strategy: none` and express any required spike, prototype, or proof plan as a finding; never recommend `design` again or append another workflow.
