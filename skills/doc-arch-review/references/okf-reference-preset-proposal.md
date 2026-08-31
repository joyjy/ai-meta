---
title: OKF reference preset proposal
status: draft
source: _Drafts/okf-pure-html-reference-preset.md
---

# OKF Reference Preset Proposal

This note preserves OKF reference-preset details that are intentionally not
part of the main `doc-arch-review` workflow yet.

## Goal

OKF core standardizes the minimum Markdown knowledge contract:

- identity: file path
- metadata: YAML frontmatter
- relationship: Markdown links
- content: Markdown body
- navigation/history: `index.md` / `log.md`

Reference presets are an extension for describing how a link should be
displayed in a specific occurrence. They must not become part of OKF core or
make the core document unreadable without a specialized renderer.

## Recommended Baseline

Use a normal Markdown link as the portable base, with companion HTML comment
metadata:

```markdown
<!-- okf-ref target="./tables/customers.md" mode="preview" label="Customers" -->
[Customers](./tables/customers.md)
```

Properties:

- Standard Markdown renderers still show a normal link.
- Agents and viewers can parse the `okf-ref` metadata.
- The format does not depend on MDX, MyST directives, Docusaurus directives, or
  Obsidian-specific syntax.
- The comment should stay close to the link it describes.

## Optional Custom Element

If a clearer DOM representation is needed, a custom element can be considered:

```html
<okf-ref target="./tables/customers.md" mode="preview" label="Customers">
  <a href="./tables/customers.md">Customers</a>
</okf-ref>
```

This is higher risk because some Markdown pipelines, CMS tools, static-site
generators, or sanitizers may remove unknown tags.

## Not Recommended As The First Step

Avoid directive-only references as the portable baseline:

```markdown
::ref{target="./tables/customers.md" mode="preview"}
```

Directive syntaxes are not CommonMark and vary across MyST, remark-directive,
markdown-it, Hugo shortcodes, and other ecosystems.

Avoid using `<pre>` as a reference container:

```html
<pre target="./tables/customers.md" mode="preview">Customers</pre>
```

`pre` means preformatted text and is easy for renderers, styles, and readers to
interpret as code-like content instead of a relationship container.

## Mode Draft

`mode` describes the display intent of one reference occurrence, not an
inherent property of the target document.

Candidate values:

- `link`: normal hyperlink.
- `preview`: hover card, side panel card, or inline summary.
- `footnote`: generated footnote marker and explanation.
- `embed`: embedded target file or section.
- `cite`: source citation only.

The same target can use different modes in different contexts, so mode belongs
next to the reference occurrence.

## Layering

```text
OKF core
- Markdown file
- YAML frontmatter
- normal Markdown links

OKF reference preset extension
- HTML comment companion metadata
- optional custom element representation
- renderer-specific adapters

Derived/rendered views
- footnotes
- hover previews
- embedded sections
- backlinks
- graph view
```

## Open Questions

- Whether GitHub, Docusaurus, Obsidian, and MkDocs preserve HTML comments and
  custom elements consistently enough.
- How MDX/Docusaurus compiles custom elements mixed with Markdown links.
- Whether blank lines, list items, tables, or wrapping between a comment and its
  link affect reliable parsing.
- Whether `target` should always be relative, or whether bundle-root absolute
  paths are allowed.
- Whether `embed` requires `section`, `heading`, or `block` targeting.
