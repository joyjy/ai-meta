# Implemented History Placement

Read when reviewing architecture docs, ADRs, or durable docs after implementation, when closing out a plan, or when deciding whether historical rationale belongs in code, docs, an ADR, or nowhere durable. The main skill loads `decision-records.md` directly when ADR admission is also in question.

- Describe the current system as current facts in target-state wording; after implementation, no durable doc keeps draft, phase-plan, or "first version / second version" voice unless a rollout phase is still an active compatibility fact. Do not retain a long implementation path when code structure already makes the behavior obvious.
- Keep history only when a future maintainer could plausibly misread the code as a bug, remove a safety exception, simplify away a compatibility boundary, or question a long-lived cross-boundary choice.
- Prefer a short source comment next to an unusual local code path. Architecture docs may point to that anchor but should not duplicate the incident narrative. A rejected or removed addition is not itself a reason to keep history or a comment about its absence.
- Use an ADR only when the choice independently passes ADR admission. Routine fixes, cleanup rationale, current-session recovery, and ordinary migration steps belong in a comment, plan archive, work log, or no durable artifact.
- `AGENTS.md` carries only rules that directly change agent behavior; it does not absorb retrospectives, full design rationale, or implementation walkthroughs.

## Plan Closeout

A project `docs/plan/` holds unfinished plans only. Before deleting an implemented, superseded, or stale plan, verify:

- Current architecture facts moved into repo durable docs, and those docs stand alone as the current target state.
- Long-lived decisions that pass ADR admission moved into ADRs; execution steps, temporary investigation, and historical commentary did not move into durable docs.
- Unimplemented ideas moved to backlog or context, or the user dropped them.
- The plan holds no unique fact needed for review or future maintenance.

Then list the exact plan paths and delete only after confirmation. A partially implemented plan stays until its unimplemented part has a home or is dropped.
