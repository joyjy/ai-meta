---
name: doc-arch-review
description: Review architecture and durable docs for correctness, completeness, ownership, source-of-truth boundaries, change guidance, ADR fit, source maps, OKF and doc-root layering.
---

# doc-arch-review

Find architecture-doc gaps that could mislead implementation, migration, ownership, or operations. Default to review-only.

## Routing

- Start with the named artifact and minimum adjacent docs. Read unrelated source only when a small file must verify a claim.
- Repo architecture, documentation architecture, or source-map review: read `references/repo-architecture-review.md` and `../../docs/architecture/source-map-contract.md` directly.
- ADR admission, placement, or review: read `references/decision-records.md`. Post-implementation history placement additionally reads `references/history-placement.md`.
- OKF / knowledge bundle / doc-root taxonomy review: read `references/okf-standard.md`; read `references/okf-spec.md` only for unresolved conformance or claimed conflict.
- OKF architecture restructuring or BMAD compatibility: directly read `references/okf-architecture-layout.md`.
- OKF preview / footnote / embed / citation behavior: directly read `references/okf-reference-preset-proposal.md`. New OKF object proposals directly use `templates/okf-knowledge-object.md`.
- Mixed evidence levels: directly read `../engineering-exit/references/evidence-classification.md`; keep output in domain language.

## Boundaries

- Entry-doc slimming, duplicated rules, context cleanup, and loading-path migration belong to `agent-doc-hygiene`; report exact duplication paths, and include only already-authorized small dedupes.
- Durable docs hold current facts, boundaries, decisions, invariants, and change guidance. Pure plans belong under `docs/plan/` in the project-control directory that owns the project's `index.md`; this directory may be separate from the source repo. Never infer a plan destination from the current repo or worktree, and do not place an unimplemented plan in source-repo `docs/` unless the user explicitly names that repo path. ADR is not the default.
- Preserve valid topology, ownership, source pointers, decisions, and safety history. Markdown and ordinary links remain the portable source; renderer views are enhancements.

## Review Axes

- **Completeness**: material scope, audience, topology, ownership, flows, source map, invariants, risks, freshness, and change guidance exist.
- **Correctness**: paths, modules, commands, generated artifacts, flows, owners, and pointers match authoritative reality.
- **Consistency**: nearby docs do not conflict or place one fact under competing owners.
- **Maintainability**: current facts stay separate from plans, history, rules, and runbooks; links remain stable.
- **Change guidance**: maintainers can see boundaries, affected layers, validation, owners, decisions, and risks.

## Severity

- `P0`: directs a dangerous or impossible change.
- `P1`: unclear or wrong boundary/source of truth/risk likely causes a bad implementation or operation.
- `P2`: missing or duplicated architecture context creates meaningful maintenance cost.
- `P3`: worthwhile clarity or terminology issue unlikely to cause a bad decision.

## Workflow

1. Fix the review target and whether edits are authorized.
2. Load route-triggered direct references and verify claims against authoritative paths or systems.
3. Apply the five axes; promote missing context to a finding only when it can change a decision.
4. Separate architecture, documentation-layer, completeness, and preflight-only signals.
5. Put severity-ordered findings first with exact evidence and a correction or decision.
6. For authorized edits, preserve decisions, move content only to a clear owner, then verify links, paths, pointers, doc-root rules, and decision usefulness.

## Output

For review-only work, use only applicable sections: `Findings`, `Completeness`, `Source Health Signals`, `Open Questions`, `Overall`. If no material finding exists, say so and name residual unverified scope. For edit work, report files changed, content moved or retained, quality improvement, and verification.
