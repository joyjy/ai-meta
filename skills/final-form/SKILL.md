---
name: final-form
description: Turn a request, context next step, GTD item, or follow-up into an executable final-form for Codex, Symphony, or a human. Use when the user says ff, final form, work order, clarify the requirement, make this dispatchable, prepare for Symphony, or asks whether a next step is ready to execute.
---

# final-form

Compile nearly executable intent into the smallest specification preserving scope, acceptance, and the next authorization boundary. It does not execute work or act as a runtime ledger.

## Core Rules

- Keep chat within 12 lines. Show `Goal`, `Scope`, and `Acceptance` once each; group multiple clauses on that line with compact numbering or semicolons.
- Use `final-form` in prose/headings; reserve `ff`/`/ff` for invocation and `ff` for the machine schema key.
- Show optional fields only when task-specific; omit empty groups and inert machine metadata.
- Fill known facts. Ask only about scope, acceptance, destructive/remote action, data model, file layout, compatibility, responsibility, or dispatch target.
- Any deletion stays blocked until its exact paths are listed and the user confirms that exact list; conceptual cleanup approval is not dispatch authorization.
- Default ordinary naming, formatting, paths, and implementation details.
- Resolve “这些” or “全部问题” to exact antecedents. Ambiguity blocks; machine scope/acceptance must cover every item before chat groups them.

## Effect-delta Admission

Use this only when a known target admits materially different terminal effects, such as link/close, reply/resolve, update/publish, or organize/delete.

- Compile the narrowest supported effect; convenience never authorizes stronger lifecycle, destructive, publication, delivery, or remote-write effects.
- Put requested and excluded stronger effects in task-specific `constraints`; show `Effect` only when it changes execution.
- If the choice changes scope, authority, or acceptance, stay not Ready and ask one question. Skip for read-only/discussion work, ordinary implementation choices, or an unambiguous contract.

## Routing

- If structural choices remain, route to `grill` and ask the first one; continue when choices are coupled. Term collisions across direction, owner, or responsibility are structural ambiguity.
- Existing-session/client continuation is structural. Read `references/work-order-contract.md`; prove each surface/activity pair and delivery semantics before Ready.
- A repeated stable event → manual routing → bounded agent step → verifiable artifact is a rollerskate signal. Evaluate it through the `automation_candidate` contract in `references/work-order-contract.md`; emit only advisory metadata, never Run authorization.
- Do not inflate an executable request to populate fields.
- Ready Codex work needing substantive checkpoints, iterative verification, or recovery is controlled execution: offer agent-owned `/ll` dispatch.
- Show one action line: while blocked show only `Blocking question`; when Ready show only `Next`.
- If an exact displayed destructive/effect list is the only blocker and `/ll` the sole execution route, one question may confirm both effect and immediate handoff. A short affirmative dispatches the unchanged semantic fields without a Ready restatement. Keep them separate when any boundary is unresolved or the user asked only to prepare.
- Explicit `/ll`, `/loop`, or loop-ledger invocation supplies dispatch authorization. Compile internally and return control when structurally ready; do not show another confirmation screen.

## References

- Read `references/work-order-contract.md` for machine form, inventory, continuation, verification loops, non-default parallelization, context output, Symphony, loop-ledger handoff, or automation signals.
- Read `references/dispatch-and-regression.md` only for persistence, dispatch, post-ready correction, verification evidence, or regression handling.

References are direct and do not route onward.

## Workflow

1. Gather request, decisions, paths, capability evidence, dirty boundary, and exact antecedents. Resolve and confirm deletion paths before Ready.
2. Write one observable goal, narrow include/exclude scope, and 2–4 observable acceptance conditions; cover every antecedent before grouping.
3. Load the machine contract only when gated. Add inventory for restore/absorb/migrate/rewrite/replace/extend, continuation for an existing session/client, verification loops when results drive revision, and parallelization only for real parallel slices.
4. Ask only the first blocker. Mark Ready only when scope is complete and the receiver can start without reinterpretation.
5. Show the single action using the Routing gates above. A substantive correction updates machine fields/revision identity and expires prior authorization.

## Chat Output

Use this sparse shape, omitting empty optional lines:

```markdown
final-form:
- Goal: <one outcome>
- Scope: <include; material exclude>
- Acceptance: <2-4 observable conditions>
- Effect: <requested effect; stronger effects not authorized, only when effect-delta admission applies>
- Constraints: <task-specific gates only>
- rollerskate automation: <fit|partial; evidence, missing gates, smallest experiment; only when applicable>
- Blocking question: <only when blocked>
- Ready: <yes|no>
- Next: <only when Ready>
```

For controlled Codex execution, use `Next: 是否由我将此版本分发给 /ll，编译 loop-ledger contract、校验并创建 Codex goal？`

When routing to grill, state that structural ambiguity remains and ask one structural question.

Outside explicit invocation, do not persist context or start loop-ledger. Confirmation authorizes only the displayed boundary; route it without asking again. loop-ledger owns machine compilation and goal creation, so do not edit implementation first.
