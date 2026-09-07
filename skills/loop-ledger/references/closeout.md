# loop-ledger-checkpoints-and-closeout

Read this reference only for checkpoint policy, risk verification, feedback/friction disposition, final audit handoff/settlement, archive, or engineering-exit handoff. Do not load it for startup or an ordinary Focus turn.

## Checkpoints And Risk

- Run `verify-ll-contract <exact-path>` before dispatch, high-risk actions, state transitions, and final exit. Full and strict runs cover discovery inventory, plan, implementation, verification, and pre-final; stop at the earliest gap.
- Execute one bounded checkpoint at a time. After at most two repair cycles for the same failure, stop as `blocked` or `needs_human` unless new evidence or an approved fallback appears.
- For unfamiliar bootstrap chains, record source, trigger command, downstream behavior, network effects, and credential or persistence surfaces. Dynamic or network-loaded execution remains low-confidence until a visible preflight proves it.
- Discover the project-native linttest/lintest gate without changing or executing it unless authorized. A template or copied example is not evidence; do not invent a gate when no stable one exists.
- Resolve Git and other side-effect authority from the user request, global rules, and the verified contract. A loop-ledger adds no permissions and does not require renewed approval for actions already authorized. `engineering-exit` privileged git exit applies only within its scope and repo flow; deletion and unrelated remote state retain their own gates.

## Feedback And Friction

Append a current-task correction as `current_task_correction` and, when necessary, a contract patch. Apply it before resuming. When the correction rejects or removes an addition, close it without residue: remove implementation plus comments, docs, tests, config, changelog, or MR text whose only purpose is to explain that addition, so the final artifact reads as if it never existed. Retain only independently evidenced current safety, compatibility, or external-contract constraints. At a ready exit, apply the correction, route unresolved task work to `next_ff_ready`, or discard it with a reason.

Do not write reusable `loop_process_gap`, `tool_route_friction`, or `doc_rule_gap` feedback in new runs; retain those types only for legacy reads. The independent `agent.audit.v1` lane classifies reusable final-form, loop-ledger, prompt, and execution gaps from rollout evidence.

Objective friction stays separate until claimed. After the exact loop-ledger verifies, a context-backed run may claim only events owned by that route and checkpoint only explicit event ids. Treat objective friction as evidence, not loop-ledger user feedback; inference alone cannot block completion.

## Exit And Archive

- Final output declares one of `done`, `commit_ready`, `needs_human`, `blocked`, `partial`, `handoff`, `save_context`, `remote_write_ready`, or `next_ff_ready`.
- Use `done` only when every `done_when` condition has external evidence and the effective appended state verifies.
- Structural follow-up exits as `next_ff_ready` with next action `next_ff`; do not execute that final-form inside the completed run.
- Terminal events remain in the same file. `/ll` never moves or archives it.
- `engineering-exit` verifies and hands off the exact ledger but does not dispatch, wait, or archive. An explicit audit request may dispatch. The later settlement caller archives only the receipt-bound ledger; the helper verifies first and moves a legacy feedback sidecar only when its exact path exists.
- The independent audit reviews execution friction and prompt/contract fidelity. It does not revalidate implementation quality or gate the user-visible engineering exit; the ledger verifier remains the oracle for checkpoints, done conditions, feedback dispositions, scope, and effective exit state.
