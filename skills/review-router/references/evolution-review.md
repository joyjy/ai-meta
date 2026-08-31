# Evolution Review

Use evolution review only inside a workflow that supplies persistent revision and round state. It coordinates review across changing artifacts; it is not a heavier one-shot checklist.

## Caller Contract

Require the caller to supply:

- stable work or review id;
- current immutable revision or artifact fingerprint;
- goal, acceptance, scope, and relevant standards;
- current round and policy-defined maximum;
- previous verdicts and unresolved findings bound to their originating revision;
- verification evidence for the current revision.

If these inputs are absent, fall back to `simple`, `two-axis`, `quality`, or `prune`; do not invent persistence inside review-router.

## Round

1. Confirm the review package matches the current revision. A verdict from another revision is stale.
2. Recheck unresolved findings against the current revision and close only those with direct corrective evidence.
3. Inspect new or materially changed paths for regressions and newly introduced risks.
4. Select the smallest useful atomic strategy:
   - `simple` for each ordinary revision;
   - `challenge` at proof-critical checkpoints or final acceptance;
   - `two-axis` when spec fidelity or standards need independent passes;
   - `quality` when structural, security, performance, or code-health risk becomes material.
   - `prune` when a revision is behaviorally adequate but likely carries removable complexity, dependencies, or speculative abstraction.
5. Return `accepted`, `rework`, or `needs_human` with findings bound to the reviewed revision.

## Rework And Repair

- Product rework changes implementation behavior and consumes a caller-owned product round.
- Evidence repair updates only review evidence for the same implementation revision and does not consume a product round.
- A finding must include `problem`, `required_change`, and `required_evidence`; do not return broad advice that cannot be closed in a later round.
- Repeated polling or session resume must not duplicate a verdict or rework round for the same fingerprint.

## Ownership

review-router does not persist fingerprints, rounds, verdicts, retries, sessions, WorkItems, loop-ledger events, or arbitration state. loop-ledger, Symphony, or another harness owns those transitions and decides when the maximum round requires human arbitration.

The evolution result contains the reviewed revision, selected atomic strategy, verdict, findings, closed prior findings, remaining proof boundary, and the caller's next required action.
