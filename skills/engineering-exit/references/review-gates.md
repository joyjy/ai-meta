# Review Gates

`engineering-exit` coordinates review gates. It does not duplicate each specialist
skill's full instructions.

The main skill directly loads a specialist only when the current diff or evidence
touches that domain. Keep findings scoped to exit.
Do not chain specialist gates into broader global hygiene, release planning, or
architecture cleanup unless the user explicitly dispatches that follow-up.

## Agent-Facing Docs

The agent-doc gate applies when changes touch or reveal issues in:

- `AGENTS.md`, `CLAUDE.md`, global instructions, tool routes, commands, skills.
- Context / memory / handoff protocols aimed primarily at agents.
- Repeated rules, bloated entry docs, duplicated source-of-truth pointers, or stale recovery instructions.

When called from `engineering-exit`, use `agent-doc-hygiene` only as
`scope=project` / `mode=exit-gate`. Limit inspection to current-scope
agent-facing docs and directly implicated loading paths. Do not run weekly /
global hygiene, scan unrelated projects, or upgrade local findings into global
rules during exit; record cross-project findings as follow-up work instead.

Exit criteria:

- Entry docs stay thin and execution ordered.
- Long flows live in the owning skill / script / durable doc.
- Rules have a single source of truth.
- Agent-facing docs do not carry implementation history or one-off recovery notes.
- Managed source projects expose one short AGENTS pointer to `docs/architecture/source-map.md`; AGENTS, README, context, and memory do not copy the map body.

## Architecture And Durable Docs

The architecture-doc gate applies when changes touch or reveal issues in:

- Architecture docs, ADRs, contracts, API docs, OKF / knowledge docs, doc-root taxonomy.
- Boundaries, ownership, source-of-truth maps, invariants, or change guidance.
- Major source roots, workspaces, packages, services, shared contracts, generator mappings, documentation layers, or primary build/test entrypoints.

Exit criteria:

- Repo docs describe the current target state.
- OKF-like docs keep to OKF core plus explicitly established local extensions.
- BMAD-compatible architecture / ADR layout checks are owned by
  `doc-arch-review`.
- ADR recommendations pass ADR fit; routine implementation history, bug-fix
  rationale, skill behavior, or current-session recovery notes are rejected from
  ADR placement.
- Safety or compatibility history that future maintainers might remove by
  mistake is anchored in a nearby source comment when possible, with durable docs
  pointing to that code anchor instead of duplicating a long incident narrative.
- `/doc`, `/docs`, and `/knowledge` responsibilities are not mixed.
- Missing completeness perspectives are either fixed or captured as review findings.
- `docs/architecture/source-map.md` exists, is linked from the architecture index, and matches current source roots, ownership, generated-source mappings, documentation layers, and validation entrypoints whenever a structural trigger is in scope.

## Release Preflight

Use release preflight for service or deployable changes before MR / PR package
reconciliation. This gate prepares release-quality evidence; it does not replace
the arch-hub `release::candidate` workflow.

Resolve `gitlab.flow` from project `index.md` only:

- `l1`: required gate for strict engineering release flow. Release-impact
  unknowns block readiness unless they can only be answered after merge; exact
  post-merge actions must be recorded.
- `l2`: warning gate for transitional release flow. Non-critical unknowns may
  proceed only with explicit user risk acceptance.
- `l3`: not applicable by default. Do not require release compatibility for
  personal / no-lint flows unless the user or project asks for release readiness.
- missing / unknown flow: report the metadata gap and do not infer a stricter or
  looser flow from repo names or remotes.

Check release-quality dimensions when relevant:

- Validation evidence: changed cases, relevant regression slice, CI or manual
  path, and skipped checks with reason.
- Release pack inputs: issue / AR / MR links, service repo / owner, final build
  items that must be filled after merge, and test-environment deployment
  expectation.
- Runtime release compatibility: mixed old/new pods during gray release, config
  ordering, service dependency rollout order, DDL / SQL, MQ / message shape,
  network / gateway / whitelist, cache / data preparation, idempotency,
  user-visible state, rollback order, and irreversible high-risk actions.

Do not convert release compatibility into speculative legacy support. If an API,
CLI, config key, or route should keep an old entrypoint, require a real caller,
external protocol, migration cost, or explicit release-window reason; otherwise
prefer the canonical target shape and record release rollout risks separately.

## Source Checks

Prefer checks in this order:

1. Commands specified by project instructions.
2. Commands used by CI or package metadata.
3. Narrow checks for touched modules.
4. Smoke / acceptance checks that exercise the changed behavior end to end at
   the smallest useful scope.
5. Static sanity checks such as `git diff --check`.

Smoke / acceptance checks should match the change shape:

- CLI / script changes: run the command, `--help`, `--dry-run`, fixture, or a
  focused command path that reaches the changed behavior.
- API / service changes: run a local request, contract probe, integration test,
  or documented manual verification when local services/secrets are unavailable.
- UI changes: run the app and capture a focused browser / screenshot check when
  practical; otherwise state the manual path and viewport / state that must be
  verified.
- Docs / skill / instruction changes: run link/path/schema checks when
  discoverable, plus `git diff --check`; smoke the owning command or skill entry
  when it has a runnable path.

Do not invent a fake smoke check. If the changed behavior depends on network,
secrets, a deployed environment, or unavailable hardware, report the skipped
smoke with the exact missing dependency and any substitute evidence.

Missing smoke infrastructure is not automatically blocking. If unit tests,
dry-runs, fixtures, CI evidence, or a concrete manual verification path provide
acceptable substitute evidence, exit can proceed while marking
`冒烟 / 验收：skipped` and recording smoke coverage as a risk or
follow-up. If no smoke check exists and no substitute evidence is available, do
not mark the change ready without explicit user risk acceptance.

Report skipped checks explicitly when they are too expensive, require network /
secrets, or the command is not discoverable.

## Stop Conditions

Stop before MR preparation if:

- Dirty paths cannot be classified into safe commit groups and preserved /
  unknown groups, or their overlap makes the branch / MR package ambiguous.
- A doc lifecycle decision would delete or archive files without user approval.
- Review gates find P0/P1 issues not accepted by the user.
- Required verification cannot run and no acceptable substitute exists.
- The MR / PR description is stale and no update draft can be prepared from the
  available diff, evidence, or issue context.
