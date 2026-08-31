# Implemented History Placement

Read when reviewing architecture docs, ADRs, or durable docs after implementation, or when deciding whether historical rationale belongs in code, docs, an ADR, or nowhere durable. The main skill loads `decision-records.md` directly when ADR admission is also in question.

- Describe the current system as current facts; do not retain a long implementation path when code structure already makes the behavior obvious.
- Keep history only when a future maintainer could plausibly misread the code as a bug, remove a safety exception, simplify away a compatibility boundary, or question a long-lived cross-boundary choice.
- Prefer a short source comment next to an unusual local code path. Architecture docs may point to that anchor but should not duplicate the incident narrative.
- Use an ADR only when the choice independently passes ADR admission. Routine fixes, cleanup rationale, current-session recovery, and ordinary migration steps belong in a comment, plan archive, work log, or no durable artifact.
- `AGENTS.md` carries only rules that directly change agent behavior; it does not absorb retrospectives, full design rationale, or implementation walkthroughs.
