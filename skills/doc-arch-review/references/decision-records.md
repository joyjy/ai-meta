# Decision Records And ADR Admission

This reference defines how `doc-arch-review` should evaluate decision records and ADR suggestions. ADRs are for durable, cross-boundary architecture decisions; they are not the default home for plans, implementation logs, ordinary cleanup, or one-off MR notes.

## ADR Admission

Recommend or create an ADR only when at least one condition is true:

- The decision is long-lived and affects multiple modules, services, tools, teams, or ownership boundaries.
- There are real alternatives, and future maintainers may reasonably ask why this option was chosen.
- The decision is driven by an external constraint, such as platform behavior, client capability limits, company process, security/compliance requirements, API contracts, or upstream workflow restrictions.
- Reverting or migrating the decision would affect historical data, multiple entrypoints, or durable user workflows.

## Do Not Use ADRs For

Do not recommend ADRs for:

- Temporary plans, implementation steps, MR status, or session recovery notes.
- Coding style, test naming, or agent behavior rules; route those to `AGENTS.md`, skills, or `coding-conventions`.
- Ordinary cleanup whose current behavior is obvious from code structure.
- Documentation restructuring, naming alignment, or source-of-truth cleanup when there is no real alternative being decided.
- Provider/API fact tables, token lifecycle matrices, error-code samples, or runbooks; route those to the relevant provider docs, API specs, or operational docs.

## Placement Guidance

Use these default homes unless the target repo has a stronger local convention:

- Architecture index: current topology, boundaries, invariants, and change guidance.
- Architecture shards: stable subtopics such as exception contracts, dependency boundaries, and migration boundaries.
- ADR directory: accepted long-lived decisions that pass ADR admission.
- Provider or feature docs: protocol facts, field mappings, examples, error-code tables, and test contracts.
- Agent entry docs: only rules that directly change agent behavior.

If an ADR is added, link it from the relevant architecture entry or provider/feature doc. Do not leave ADRs as unreferenced files in a directory.
