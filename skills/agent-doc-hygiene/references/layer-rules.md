# Agent Documentation Layer Rules

Read only when the audit includes project entries, README, source maps, durable documentation, context/memory, backlog, changelog, or history placement.

## Project Entries And Source Maps

- A project `AGENTS.md` contains project goals, maintenance boundaries, local workflow, and one short early pointer to canonical `docs/architecture/source-map.md`. Do not copy the source map inventory into the entry.
- A missing or broken AGENTS source-map pointer, or a competing map in AGENTS, README, context, or memory, is `Must Fix`. Route source-map semantic accuracy to `doc-arch-review`.
- When `AGENTS.md` exists, `CLAUDE.md` is exactly the thin import `@AGENTS.md`; keep project rules out of it.
- Human-facing README files should not point readers to agent-only rules by default. If a README copies architecture, runtime, feature-manual, or agent-rule content already owned elsewhere, classify a small direct deduplication as `Must Fix`.
- Cross-project agent principles belong in global instructions; tool invocation details belong in tool routes; reusable workflows belong in skills; architecture facts belong in durable docs.

## Durable And Operational Layers

- Architecture topology, boundaries, ADRs, and long-term decisions live in durable docs. Ordinary procedures, skill behavior, implementation plans, preferences, and session history do not become ADRs.
- Keep `/doc` for tool-facing or generated-doc inputs, `/docs` for engineering durable docs, and `/knowledge` for long-lived domain knowledge. Do not merge these roots to reduce file count.
- Engineering operation details belong in coding conventions or their templates.
- Human and durable docs are secondary hygiene targets: inspect them only to resolve duplication, routing, or source-of-truth ownership.

## Context And History

- Context and memory keep only Doing, Blocked, Next Steps, and Critical Context. Move durable facts to their owning docs.
- Project `index.md` Backlog holds unfinished or follow-up-worthy work. Completed items may remain briefly as a recent buffer, then move to `changelog.md` or the project equivalent.
- Changelogs contain completed history, not active tasks. Do not move implementation history into hot agent entries.
- Preserve effective rules, unfinished work, blockers, and key decisions while slimming. Avoid overfitting a single correction unless it had clear impact and the fix is a short route or source-of-truth move.
