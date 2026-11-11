# design-direction-persistence

Use only after the user explicitly asks to lock or save an accepted direction.

## Target Resolution

1. Resolve the personal project root as the directory that owns the project's `index.md`.
2. Treat `DESIGN.md` and `design.md` as the same candidate on case-insensitive filesystems.
3. Do not fall back to cwd or a source-repo root when the personal project root is unresolved.
4. Do not write a personal `DESIGN.md` into a team or external repo. Team/source-repo design artifacts remain evidence unless separately authorized.
5. If several personal candidates could own the contract, ask which one is authoritative.

## Confirmation And Write

Read the Google Stitch DESIGN.md specification from `~/Documents/reference/design.md/docs/spec.md` ([official upstream](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md) if absent). [Impeccable uses the same specification](https://impeccable.style/docs/document/). Show the proposed contract and obtain confirmation before writing `<project-root>/DESIGN.md`. An explicit request to save the already displayed and accepted contract is sufficient; ask again only when the target or contract changes.

- Put structured tokens in YAML frontmatter. Use confirmed values from the project's canonical tokens or components. Omit unknown values and empty groups. Impeccable's structured reader extracts tokens from frontmatter, so keep token YAML out of fenced blocks in the body.
- Use the spec's canonical section headings and order. Omit irrelevant sections. Put the audience, primary job, and visual intent in `Overview`. Put observable rules in the relevant sections or `Do's and Don'ts`. Link the original token or component source where it explains a rule.
- Keep the document focused on durable design decisions. Leave task plans, audits, historical versions, and exact implementation behavior in their owning artifacts.

Read an existing candidate completely. Update an already conforming file in place and keep one current statement per rule. If an existing file needs conversion, show the mapping and include the conversion in the confirmed scope before writing. Preserve unrelated content and keep one authoritative file.

After writing, verify that the saved file matches the confirmed contract and the spec. Run the official linter if available. If the project also uses Impeccable, verify its resolved `designPath` before claiming it auto-loads this file. An Impeccable session started in a separate source checkout may resolve a different context root.

`coding-conventions` may point relevant frontend sessions to this personal artifact, but must not copy this workflow or inject its personal path/content into team instructions. Keep human-facing explanation in README/design docs and agent execution constraints in `AGENTS.md`.
