# final-form-contract

This is the canonical sparse v0 machine-facing shape. Required fields form the initial requirement; gated fields appear only when needed. Omitted fields use the documented default and must not be serialized as empty groups merely to complete the schema.

## Sparse Shape

```yaml
ff:
  goal: ""
  scope:
    include: []
    # exclude: []                 # only material exclusions
  acceptance: []
  # constraints: []              # only task-specific safety or compatibility gates
  # defaults: []                 # only choices useful to the executor
  # checks: []                   # explicit commands or justified substitutes
  # existing_capability_inventory: {} # restore/migrate/replace/extend only
  # continuation: {}             # existing session/client delivery only
  # verification_loop: {}        # iterative verification only
  # parallelization: {}          # non-default mode only
  # automation_candidate: {}     # advisory rollerskate fit only; never dispatch authorization
  blocking_questions: []
  ready_for_dispatch: false
  dispatch_target: codex
  # output_target: context        # persistence only
  # origin_session_id: null       # cross-session handoff only
```

## Required Semantics

- `goal`: one observable outcome sentence.
- `scope.include`: exact files, modules, systems, tickets, or behavior to touch.
- `scope.exclude`: only known dirty changes, tempting nearby work, or prohibited actions that materially protect scope.
- `acceptance`: 2-4 observable conditions another agent can verify.
- Referential scope: when the user authorizes an earlier list by shorthand such as “these” or “all issues”, resolve the exact antecedent before compilation. Every referenced item must be represented in `scope.include`, `acceptance`, or both. A compact grouped condition is valid only when it preserves the behavior and boundary of every item; an ambiguous antecedent keeps final-form blocked.
- `blocking_questions`: at most one active pre-dispatch question.
- Deletion authorization: conceptual cleanup or removal intent is insufficient. Put the exact target paths in scope and keep one confirmation question blocking until the user approves that exact list.
- `ready_for_dispatch`: true only when `blocking_questions` is empty and the receiver can start without reinterpretation.
- `dispatch_target`: `codex`, `symphony`, `manual`, or `unknown`.

## Gated Fields

- `constraints`: task-specific safety gates, remote-write or deletion boundaries, compatibility rules, and required source-of-truth layers. Global rules stay global.
- `defaults`: non-blocking choices that prevent needless re-asking; omit ordinary conventions already discoverable from the repo.
- `checks`: commands, smoke tests, dry-runs, state checks, or explicitly justified substitutes.
- `existing_capability_inventory`: only for work that restores, absorbs, migrates, rewrites, replaces, or extends existing behavior. Include only populated capability classes among prior entries, behavior rules, runtime data sources, runtime integrations, domain roles, and counterexamples.
- `continuation`: required when the goal resumes or delivers into an existing session, chat, or client. Record only proven target pairs and their delivery semantics:

  ```yaml
  continuation:
    supported_targets:
      - surface: codex_desktop
        activity: idle
        transport: chat_session
    admission: "how the target accepts or rejects concurrent delivery"
    queue_visibility: "where queued work is visible, or explicitly none"
    completion_visibility: "where the user observes terminal delivery"
    idempotency: "identity and duplicate-delivery behavior"
  ```

  `activity` is explicitly `idle` or `active`; represent both as separate proven targets. A missing or unknown target dimension that affects claimed scope keeps `ready_for_dispatch: false`. Success on one target pair is not evidence for another.
- `verification_loop`: only when verification changes the implementation. It may contain trigger, current-agent loop, cold-start checks, stop conditions, and retained artifacts; omit unused subfields.
- `parallelization`: omit for `main_agent`. For `tool_parallel` or `readonly_subagents`, record narrow tasks and one reason.
- `automation_candidate`: only when the request matches the stable-event / bounded-agent / verifiable-artifact signal in `../../coding-conventions/patterns/event-admitted-bounded-agent-run.md`. It is advisory and never changes `dispatch_target`, `ready_for_dispatch`, current-task authorization, or loop-ledger runtime authority:

  ```yaml
  automation_candidate:
    runtime: rollerskate
    fit: fit # fit | partial
    evidence: [<source or implementation anchor>]
    # missing_gates: [<exact unproven gate>] # required for partial
    smallest_experiment: <bounded one-shot verification>
  ```

  `runtime` is exactly `rollerskate`; `fit` and `partial` follow the pattern's recognition gates. `partial` requires non-empty `missing_gates` and must not recommend automatic Run admission. `evidence` and `smallest_experiment` are non-empty for both values. Omit the whole object when the signal is absent; never serialize `not_fit` or an empty candidate.
- `output_target`: use `context` only for saved or cross-session recovery output; ordinary chat defaults to `chat` without serializing it.
- `origin_session_id`: capture the creator's stable thread id only when final-form crosses context, GTD, Symphony, rework, or handoff boundaries.

## loop-ledger-compatibility

- `goal` seeds loop-ledger outcome and runtime objective.
- include/exclude scope seeds required artifacts and out-of-scope boundaries.
- acceptance plus verification-loop stop conditions seed `done_when`.
- checks seed commands, state checks, or substitute evidence.
- constraints seed allowed side effects, ask-before gates, and call-user conditions.
- blocking questions stop loop-ledger as `needs_human` before execution.
- existing capability inventory requires acceptance provenance in loop-ledger; missing provenance is an acceptance gap.
- continuation targets and delivery semantics seed runtime binding, scope limits, and `done_when`; an unsupported or unproved surface/activity pair is an acceptance gap.
- `automation_candidate` is excluded from loop-ledger authority, runtime binding, `done_when`, dispatch target, and dispatch readiness; it remains optional advisory metadata if a caller preserves it.
- user confirmation authorizes only the displayed revision and never becomes the objective.
- referential authorization covers the resolved antecedent set, not a model-selected subset; loop-ledger input must preserve that set even when the human final-form display groups it compactly.
- a term collision that assigns one name to different directions, owners, or responsibilities is not wording polish: distinguish the roles before `ready_for_dispatch: true`.
- every compiled loop-ledger `done_when` item preserves one ordered `acceptance_sources` entry; final-form acceptance and verification-loop stop conditions must not be silently dropped, merged, or invented.
