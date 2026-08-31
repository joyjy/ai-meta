# final-form-dispatch-and-regression-gates

Read this reference only after a persistence, dispatch, post-ready correction, verification-loop, or regression gate is hit.

## Persistence

- Context output nests the sparse `ff` object under the selected route's `Next Steps` and sets `output_target: context`.
- Do not write context from final-form alone. Use `~/.ai/scripts/context-ff-merge <abbr[:route]> --ff-file <file>` after persistence is requested.
- Preserve unrelated routes. If a new final-form would replace an unrelated active next step, ask one blocking question.
- A missing context may be initialized as context.v2 with an active mainline and no workstreams.
- Invalid abbr or route names stop before writing.
- Ordinary recovery notes, unfinished Doing, candidate follow-ups, and recurring automation stay prose rather than becoming final-form.

## Dispatch

- `ready_for_dispatch: true` means the receiver executes rather than reopening discovery.
- For ready Codex work that needs controlled execution or recovery, explicitly offer agent-owned `/ll` dispatch; when Codex goals are available and stop conditions are stable, ask whether the agent should compile the displayed final-form into a loop-ledger contract and start a goal.
- The displayed final-form action supplies the explicit `/ll` boundary. A short user reply such as `OK`, `可以`, or `实施` confirms that displayed dispatch, and the agent routes into `/ll` on the user's behalf; do not require the user to repeat `/ll`.
- An explicit `/ll <task>`, `/loop <task>`, or loop-ledger skill invocation supplies that boundary up front. Compile final-form internally and dispatch in the same turn when ready; do not display a second authorization prompt.
- Do not present direct implementation as the dispatch action for controlled Codex work. A short confirmation is authorization for the displayed `/ll` dispatch, never permission to bypass it.
- final-form never creates a goal. Confirmed `/ll` dispatch owns compilation, verification, and adapter selection.
- Before the `/ll` handoff starts, neither final-form nor the following turn may modify implementation files. The expected first evidence is loop-ledger startup, an exact session path, successful contract verification, and Codex goal creation or a concrete `needs_human` result.
- A substantive correction updates the current revision and expires earlier dispatch authorization. Show changed human fields and ask again.
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
2. Expire prior dispatch authorization and show the changed human fields.
3. If a loop-ledger run is active, append `current_task_correction` and a contract patch
   when scope, acceptance, authorization, or runtime binding changed.
4. Leave reusable cause classification to the independent `agent.audit.v1`
   prompt/contract lane at loop-ledger closeout or `save-context`; final-form keeps no regression
   store and does not self-promote a correction into objective friction.
5. After an accepted final-form rule change, replay the failure case; use cold-start
   evidence when dispatchability is the claim.

Regression examples: a multi-checkpoint implementation must explicitly offer agent-owned `/ll` dispatch, and a direct loop-ledger invocation must start without first displaying that offer. After either boundary is satisfied, loop-ledger starts; it must neither ask for `/ll` again nor continue directly into implementation before creating the loop-ledger session. A request for an arbitrary current Codex session to receive a callback cannot be Ready until surface, activity, transport, admission, queue visibility, completion visibility, and idempotency are established; evidence for an idle chat session narrows final-form to that pair and leaves active Desktop or CLI feasibility outside the accepted scope.

For referential-scope regressions, replay a prompt that authorizes an earlier multi-item proposal with shorthand such as “do all of those”. The machine-facing final-form passes only when every antecedent item is recoverable from scope or acceptance, including less prominent structural or payload-boundary items; a concise human summary is not evidence if the machine form dropped one.

Read-only subagents remain internal owner-managed investigation. They do not create user-owned Codex threads or own edits, Git actions, or final judgment.
