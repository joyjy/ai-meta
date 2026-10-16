# final-form-dispatch-and-regression-gates

Read this reference only after a persistence, dispatch, post-ready correction, verification-loop, or regression gate is hit.

## Persistence

- Context output nests the sparse `ff` object under the selected route's `Next Steps` and sets `output_target: context`.
- Do not write context from final-form alone. Use `~/.ai/scripts/context-ff-merge <abbr[:route]> --ff-file <file>` after persistence is requested.
- Preserve unrelated routes. If a new final-form would replace an unrelated active next step, ask one blocking question.
- A missing context may be initialized as context.v3 with an active mainline and no workstreams.
- Invalid abbr or route names stop before writing.
- Ordinary recovery notes, unfinished Doing, candidate follow-ups, and recurring automation stay prose rather than becoming final-form.

## Dispatch

- `ready_for_dispatch: true` means the receiver executes rather than reopening discovery.
- Follow loop-ledger's Admission rules for automatic selection and platform goal authority. Ask about starting a goal only when that authority is missing. An ordinary ready task returns to its caller; complexity alone does not mandate a ledger.
- The displayed final-form action supplies the explicit `/ll` boundary. A short user reply such as `OK`, `可以`, or `实施` confirms that displayed dispatch, and the agent routes into `/ll` on the user's behalf; do not require the user to repeat `/ll`.
- When a fully displayed exact destructive/effect list is the only blocker and `/ll` is the sole execution route, one question may authorize both effect and immediate handoff. A short affirmative clears the blocker; compile unchanged goal, scope, acceptance, effect, and constraints with `ready_for_dispatch: true`, then hand off without replaying a Ready version. Keep the boundaries separate if any of them remains unresolved or the user asked only to prepare.
- An explicit `/ll <task>`, `/loop <task>`, or loop-ledger skill invocation supplies that boundary up front. Compile final-form internally and dispatch in the same turn when ready; do not display a second authorization prompt.
- Do not present direct implementation as the dispatch action for controlled Codex work. A short confirmation is authorization for the displayed `/ll` dispatch, never permission to bypass it.
- final-form never creates a goal. Authorized `/ll` dispatch owns compilation, verification, and adapter selection.
- When `/ll` is selected, the first execution evidence is loop-ledger startup, an exact session path, successful contract verification, and Codex goal creation or a concrete `needs_human` result, before implementation edits.
- A substantive correction updates the current revision. Show the changed human fields; ask only when the delta exceeds authorization, including authorization supplied by the current correction.
- Symphony requires concrete cwd, include scope, acceptance, and safety constraints. Carry the original session id when origin-session review is expected.

## Verification Loop

- Coding loops normally implement, run the relevant check, inspect failures, patch, and rerun until conditions pass or a concrete blocker is proved.
- Skills, classifiers, routing rules, reports, workflow contracts, context recovery, and agent docs may retain sample input, draft, critique, revision, and final evidence.
- Use cold-start validation only when another agent must execute the artifact without chat history; it never replaces hard local checks.
- Stop conditions describe behavior quality or terminal state, not merely a fixed round count.

## Correction And Audit Handoff

Handle a substantive correction in the active final-form immediately; do not
depend on later audit to repair current scope or acceptance.

1. Amend the current final-form first.
2. Show the changed human fields and recheck the affected authority boundary; an explicit correction can authorize that delta without a second confirmation.
3. For an active loop-ledger, hand the correction to its owner to apply the effective adapter/goal-binding protocol. final-form must not prescribe a structural `contract_patch` to a goal-bound run or reopen a completed run.
4. Leave reusable cause classification to an explicitly requested independent `agent.audit.v1`
   follow-up; final-form keeps no regression
   store and does not self-promote a correction into objective friction.
5. After an accepted final-form rule change, replay the failure case; use cold-start
   evidence when dispatchability is the claim.

Regression examples: authorized work needing durable phase tracking selects loop-ledger automatically, but does not create a goal when the platform requires missing explicit authorization; short tasks and discussion return to the caller without mandatory `/ll`; direct `/ll` invocation starts without another offer. Once selected and authorized, loop-ledger neither asks again nor edits before session creation. If only an exact deletion list blocks and one question combines its confirmation with `/ll`, `OK` starts loop-ledger without replay. A callback to an arbitrary current Codex session cannot be Ready until surface, activity, transport, admission, queue visibility, completion visibility, and idempotency are proved; evidence for an idle chat narrows scope to that pair.

For referential-scope regressions, replay a prompt that authorizes an earlier multi-item proposal with shorthand such as “do all of those”. The machine-facing final-form passes only when every antecedent item is recoverable from scope or acceptance, including less prominent structural or payload-boundary items; a concise human summary is not evidence if the machine form dropped one.

Read-only subagents remain internal owner-managed investigation. They do not create user-owned Codex threads or own edits, Git actions, or final judgment.
