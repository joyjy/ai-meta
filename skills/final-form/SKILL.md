---
name: final-form
description: Turn a request, context next step, GTD item, or follow-up into an executable final-form for Codex, Symphony, or a human. Use when the user says ff, final form, work order, clarify the requirement, make this dispatchable, prepare for Symphony, or asks whether a next step is ready to execute.
---

# final-form

Compile nearly executable intent into the smallest specification preserving scope, acceptance, and the next authorization boundary. It does not execute work or act as a runtime ledger.

## Core Rules

- Keep chat within 12 lines; always show `Goal`, `Scope`, and `Acceptance`.
- Use `final-form` in prose/headings; reserve `ff`/`/ff` for invocation and `ff` for the machine schema key.
- Show optional fields only when task-specific; omit empty groups and inert machine metadata.
- Fill facts from context. Ask only about scope, acceptance, destructive/remote action, data model, file layout, compatibility, responsibility, or dispatch target.
- Any deletion stays blocked until its exact paths are listed and the user confirms that exact list; conceptual cleanup approval is not dispatch authorization.
- Default ordinary naming, formatting, paths, and implementation details.
- Resolve shorthand such as “这些” or “全部问题” to its exact antecedent. Ambiguous antecedents block; machine scope/acceptance must cover every item before chat may group them.

## Effect-delta Admission

Use this only when a known target admits materially different terminal effects, such as link/close, reply/resolve, update/publish, or organize/delete.

- Compile the narrowest effect supported by the request; convenience never authorizes a stronger lifecycle, destructive, publication, delivery, or remote-write effect.
- Put the requested and excluded stronger effects in task-specific `constraints`; show `Effect` only when it changes execution.
- If the choice changes scope, authority, or acceptance, stay not Ready and ask one question. Skip this gate for read-only/discussion work, ordinary implementation choices, or an unambiguous domain contract.

## Routing

- If any structural choice remains, route to `grill` and ask the first question; do not emit a guessed specification. Continue grilling when several coupled choices remain.
- A term collision across directions, owners, or responsibilities is structural ambiguity; rename the roles or ask one question.
- Existing-session/client continuation is structural. Read `references/work-order-contract.md`; prove each surface/activity pair and delivery semantics before Ready.
- A repeated stable event → manual routing → bounded agent step → verifiable artifact is a rollerskate signal. Evaluate it through the conditional pattern; emit only advisory `automation_candidate`, never Run authorization.
- Do not inflate an executable request to populate fields.
- Ready Codex work needing substantive checkpoints, iterative verification, or recovery is controlled execution: offer agent-owned `/ll` dispatch.
- An explicit `/ll`, `/loop`, or loop-ledger invocation supplies dispatch authorization. Compile final-form internally and return control to loop-ledger as soon as structurally ready; do not display another confirmation screen.

## References

- Read `references/work-order-contract.md` for machine-facing final-form, inventory, continuation, verification loops, non-default parallelization, context output, Symphony, or loop-ledger handoff.
- Read `references/dispatch-and-regression.md` only for persistence, dispatch, post-ready correction, verification-loop evidence, or regression handling.
- Read `../coding-conventions/patterns/event-admitted-bounded-agent-run.md` only when the request itself exposes its stable-event / bounded-agent / verifiable-artifact signal.

References are direct and do not route onward.

## Workflow

1. Gather request, decisions, paths, capability evidence, dirty boundary, and exact antecedents. For deletion, resolve exact paths and confirm them before Ready.
2. Write one observable goal, narrow include/exclude scope, and 2–4 observable acceptance conditions. Verify every antecedent item is represented before grouping.
3. Load the machine contract only when gated. Add inventory only for restore/absorb/migrate/rewrite/replace/extend; continuation only for an existing session/client; verification loop only when results drive revision; parallelization only for real parallel slices.
4. Ask only the first blocking question. With none, mark Ready only when scope coverage is complete and the receiver can start without reinterpretation.
5. Show the next authorization action. Offer `/ll` for controlled Codex execution; explicit loop-ledger invocation skips this display.
6. A substantive correction updates machine fields/revision identity and expires prior dispatch authorization. Never reuse confirmation after goal, scope, acceptance, authorization, or continuation changes.

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
- Next: <one authorization or owner action>
```

For controlled Codex execution, use `Next: 是否由我将此版本分发给 /ll，编译 loop-ledger contract、校验并创建 Codex goal？`

When routing to grill, state that structural ambiguity remains and ask one structural question.

Outside explicit invocation, do not persist context or start loop-ledger. Confirmation of the displayed `/ll` action authorizes only that handoff; route it without asking again. loop-ledger owns compilation and goal creation; do not edit implementation first.
