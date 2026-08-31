# design-direction-persistence

Use only after the user explicitly asks to lock or save an accepted direction.

## Target Resolution

1. Resolve the personal project root as the directory that owns the project's `index.md`.
2. Treat `DESIGN.md` and `design.md` as the same candidate on case-insensitive filesystems.
3. Do not fall back to cwd or a source-repo root when the personal project root is unresolved.
4. Do not write a personal `DESIGN.md` into a team or external repo. Team/source-repo design artifacts remain evidence unless separately authorized.
5. If several personal candidates could own the contract, ask which one is authoritative.

## Confirmation And Write

Show this compact proposed contract and obtain explicit confirmation before writing `<project-root>/DESIGN.md`:

```markdown
# Design

## Direction
<one short paragraph>

## Invariants
- <three to five durable constraints>

## Sources of truth
- <tokens, components, screenshots, prototype, or live reference>
```

Read an existing candidate completely. Preserve its purpose and unrelated content, then patch only the confirmed contract section.

The durable artifact is a human-controlled design map: long-term intent, three to five invariants, and links to real sources of truth. Do not copy tokens, component specifications, task plans, the runtime audit, or exact implementation behavior into it.

`coding-conventions` may point relevant frontend sessions to this personal artifact, but must not copy this workflow or inject its personal path/content into team instructions. Keep human-facing explanation in README/design docs and agent execution constraints in `AGENTS.md`.
