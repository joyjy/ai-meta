# Document Lifecycle

Use this reference during `engineering-exit` when a change produced plan docs,
architecture docs, ADRs, generated docs, or agent-facing instructions.

## Layering

| Layer | Path pattern | Purpose |
| --- | --- | --- |
| Project plan | `<project>/docs/plan/` | Temporary reasoning, implementation steps, draft checklists, unresolved assumptions. |
| Repo durable docs | `<repo>/docs/architecture*`, `<repo>/docs/*` | Current target-state facts, boundaries, invariants, contracts, and change guidance. |
| Repo ADR | `<repo>/docs/adr/*` or local ADR convention | Long-lived decisions that cross boundaries, have real alternatives, or are driven by external constraints. |
| Context | `~/.ai/contexts/<abbr>.md` | Recovery index: current state, Doing, Blocked, next step, and relevant files. |

## Migration Checklist

Before deleting or archiving a plan, verify:

- Current architecture facts have moved into repo durable docs.
- Long-lived decisions that pass ADR fit have moved into ADRs.
- Execution steps, temporary investigation, and historical commentary did not move into repo durable docs.
- Unimplemented ideas moved back to backlog / context / issue, or were intentionally dropped.
- Repo docs can stand alone as the current target state.
- The plan file no longer contains unique facts needed for review or future maintenance.

## Rules

- Do not put pure execution plans in repo durable docs.
- Do not leave repo docs in draft / phase-plan voice after implementation is complete.
- Prefer target-state wording over "first version / second version" wording, unless the rollout phase is still an active compatibility fact.
- Do not preserve long implementation history for behavior that is already clear
  from the code. Keep history only when it protects an unusual safety exception,
  compatibility boundary, or future maintenance decision that remains real and
  independently evidenced in the current target state. A rejected or removed
  addition is not itself a reason to preserve history about why it is absent.
- Prefer a short source comment next to unusual safety or compatibility code;
  durable architecture docs may point to that code anchor instead of repeating
  the full incident story. Do not create such a comment when no corresponding
  current code or constraint should have existed.
- Preserve detailed references by relocating them to the proper layer before trimming overview docs.
- Do not delete plan files without explicit confirmation listing exact paths.
- If the target plan belongs to a separate project layer, do not move it into the source repo just because the repo has a `docs/` directory.

## ADR Fit

Create or recommend ADR only when at least one is true:

- The decision is long-lived and affects multiple modules, tools, teams, or ownership boundaries.
- There are real alternatives, and future maintainers may ask why this option was chosen.
- The decision is driven by platform behavior, client capability, company process, security / compliance, API contracts, or upstream workflow restrictions.
- Reverting or migrating it would affect historical data, multiple entrypoints, or durable user workflows.

Do not use ADRs for task plans, ordinary procedures, current-session notes,
temporary frictions, skill behavior, or general preferences.

During `engineering-exit`, treat ADR fit as a strict admission gate: if a proposed
ADR does not meet one of the positive criteria above, leave the rationale in the
appropriate source comment, architecture note, plan archive, follow-up work
order, or issue instead of creating or recommending an ADR.
