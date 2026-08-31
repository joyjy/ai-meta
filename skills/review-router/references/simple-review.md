# Simple Review

Run one low-cost maintainer pass over the fixed target, behavior, context, and evidence.

## Review

- Prioritize correctness bugs, regressions, missing acceptance behavior/tests, and high-risk boundaries.
- Read only enough context to prove or dismiss a material concern; anchor findings to the narrowest file, line, diff hunk, test, or evidence.
- Report P0/P1 and only material P2 findings. State impact, evidence, and required correction/decision.
- Omit preferences, low-impact rearrangement, checklist narration, and invented findings.

## Next Review

Choose exactly one strategy most likely to change readiness:

- `two-axis`: originating-spec fidelity, scope creep, partial requirements, or standards tension remains unresolved.
- `quality`: material readability, architecture, security, performance, dependency, shared-module, or data-contract risk remains.
- `prune`: correctness appears adequate but removable code/dependency, native/stdlib replacement, speculative abstraction, or material shrinkage is likely; use `quality` for broader architecture/security/performance risk.
- `challenge`: current checks do not prove the real invocation, artifact, permissions, deployment, lifecycle, or consumer outcome.
- `none`: goal and behavior align, relevant checks cover the changed path, and no material uncertainty remains.

Do not escalate for diff size or checklist availability.

## Result

Return `strategy: simple`, `verdict: pass|findings`, severity-ordered findings or `no material findings`, and `next_review.strategy: none|two-axis|quality|prune|challenge` with one evidence-backed reason plus the exact unresolved question unless `none`. P0/P1 blocks readiness; the caller owns P2 disposition and fixes.
