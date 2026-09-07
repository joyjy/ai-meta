# Repository Architecture Review

Use for repo architecture, documentation architecture, canonical source-map review, or a structural change that may have invalidated ownership documentation. For source-map or structural-change review, the main skill loads `../../../docs/architecture/source-map-contract.md`; that contract owns the managed-project content and presentation requirements.

## Source Map Review

- For a managed project covered by the source-map contract, require one canonical `docs/architecture/source-map.md`, linked from the architecture entry; `AGENTS.md` carries only a short pointer. For other projects, evaluate the established ownership map without imposing personal paths or creating a competing map.
- Compare the map with repo roots, manifests, workspace/package/service metadata, build/test entrypoints, generated artifacts, architecture boundaries, shared contracts, and documentation layers.
- A missing or wrong major root, owner, shared contract, or generated-source mapping is `P1` when it can cause an incorrect change; otherwise `P2`.
- Prefer a concise fenced `text` directory tree, followed only by boundary notes and cross-cutting mappings the tree cannot express. Do not repeat the tree as a full root-by-root inventory.
- When semantics are accurate but the agent loading path is missing or duplicated, route the exact issue to `agent-doc-hygiene`; authorized small pointer fixes may stay in the same change.

## Source Health Preflight

Run a shallow preflight for repo-wide architecture reviews. For a named document or bounded exit gate, inspect only the paths needed to verify its claims or changed boundaries. This is structural evidence, not code review.

Inspect:

- file inventory via `git ls-files`, `rg --files`, or equivalent fast listing;
- source-map and architecture entrypoint presence;
- line-count hotspots, preferring `~/.ai/scripts/project-line-counts <root>` and its `--markdown` mode;
- README, AGENTS, CLAUDE, ADR directories, and accidental `AGENT.md`;
- shallow `git status --short` and, when useful, recent path churn;
- manifests, build/test metadata, CI filenames, and generated/vendor/cache paths;
- path-level alignment between documented modules/owners and the repo tree.

Do not infer implementation bugs, API behavior, or design correctness from counts or filenames alone. Report a signal under `Source Health Signals` unless it directly contradicts an architecture claim.

High-signal thresholds:

- source/config/script above about 1200 lines is a maintainability risk; above 3000 is high risk;
- Markdown above about 600 lines is a bloat risk; above 1500 is high risk;
- documented module/service splits with no matching path boundary;
- documented validation with no visible test/CI/build entrypoint;
- uncommitted changes touching reviewed docs or boundaries, making the baseline unstable.

## Repo Review Workflow

1. Resolve the repo root, architecture entry, source-map path, and review baseline.
2. Run the applicable preflight without reading unrelated implementation.
3. When the source-map contract applies, check declared roots, ownership, shared contracts, generated mappings, documentation layers, and validation entrypoints. Otherwise use the project's established documentation contract.
4. Check that common structural changes have actionable guidance and that nearby entry docs point to, rather than copy, the canonical map.
5. Keep inventory/count observations separate from proven semantic findings.
