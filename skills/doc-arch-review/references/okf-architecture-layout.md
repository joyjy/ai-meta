# OKF Architecture Layout

Read only when the user asks to restructure architecture with OKF, convert a monolithic architecture doc into a knowledge bundle, or keep architecture docs compatible with BMAD v6.

## Layout

- Prefer `docs/architecture/index.md` as the architecture entry, `docs/architecture/**/*.md` for stable scope shards, and `docs/architecture/adrs/0001-*.md` for ADRs.
- This remains BMAD-compatible when `planning_artifacts` resolves to `docs`, because BMAD can load sharded architecture under `{planning_artifacts}/*architecture*/*.md`.
- It remains OKF-compatible because files are ordinary Markdown knowledge objects linked from the architecture index; do not invent non-OKF frontmatter fields to make the layout work.

## Restructure Trigger

“Use OKF to restructure architecture”, “OKF 重构架构文档”, “像 /arch-doc 的 OKF 那样重构” or equivalent wording means converting a monolithic architecture document into a directory knowledge bundle unless the user explicitly asks to keep one file.

1. Move `docs/architecture.md` to `docs/architecture/index.md`.
2. Split stable scopes into sibling shards with local names such as `horizontal-client-consistency.md`, `vertical-agent-ll.md`, `source-of-truth-boundaries.md`, or `gates-and-release-preflight.md`.
3. Keep the index concise: scope, current topology, shard links, invariants, and change guidance.
4. Give each shard one stable owner and link it back to the index.
5. Update nearby relative links and avoid leaving a second competing `docs/architecture.md` unless an explicitly required temporary compatibility stub has a removal condition.
