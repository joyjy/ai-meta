---
name: design-direction
description: Establish or recover visual direction for new UI, substantial redesign, or a drifting interface. Use for dd, 风格跑偏, 保持现在这个感觉, or 先锁一下设计.
---

# design-direction

Use before new UI work, major redesign, or when an acceptable UI drifts. Skip tiny fixes in a clear design system. State a compact Design Read from project evidence; continue implementation only when the user's request already authorizes it. Direction discussion alone ends with the proposed direction, not edits or a runtime audit.

## Modes

- **Initialize Direction**: new UI, substantial redesign, or no clear design contract. Infer the intended surface from the request and evidence; ask only about a material unresolved choice.
- **Recover Baseline**: an acceptable UI is drifting, or the user asks to preserve its current feel. Infer what already works from its layout, density, type, color, component, control, and state language.

In recovery, preserve the existing language. Switch modes only when the user asks to change the overall style. Persistence is a gate, not a third mode.

## Conditional References

- Choose experts by the decision still open after reading project evidence. Use at most one visual-style lens; add one UX lens only for a separate interaction or data-reading decision. Read the relevant section, record the concrete choice it changed, and do not import an expert's fixed palette, implementation workflow, or persistence rules into the project. If a source is unavailable, continue from project evidence and name the gap.
- New expressive pages, demos, or playful UI → `~/Documents/reference/anthropics-skills/skills/frontend-design/SKILL.md` ([upstream](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) if absent). Brand-heavy landing or editorial work → `~/Documents/reference/taste-skill/skills/taste-skill/SKILL.md`; choose one for visual direction.
- Existing UI needing a substantial visual audit → `~/Documents/reference/taste-skill/skills/redesign-skill/SKILL.md`. Explicit warm editorial minimalism → `~/Documents/reference/taste-skill/skills/minimalist-skill/SKILL.md`; do not apply its palette to a merely restrained tool.
- Complex workflow, dashboard, chart, or graph interaction → `~/Documents/reference/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md` ([upstream](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md) if absent); use only the applicable UX or chart guidance.
- For an interactive information graphic or network map with overview, focus, or zoom decisions, read `patterns/information-graphic-navigation.md` and apply only the conditions that match the surface.
- Read `references/rendered-verification.md` when implementing or verifying the UI.
- Read `references/design-persistence.md` only after the user explicitly asks to lock or save the accepted direction.

Load only triggered direct references; local references do not route onward.

## Safety And Ownership

- `DESIGN.md` persistence requires explicit lock/save intent and confirmation of the compact proposed contract; a request to save an already displayed and accepted contract supplies that confirmation.
- Personal `DESIGN.md` belongs only at the personal project root that owns `index.md`; never infer cwd or a team/external source repo as a fallback.
- Project-native design docs in team/source repos are read-only evidence unless the user separately authorizes editing them.
- Never replace a design document wholesale. Preserve unrelated content and patch only the confirmed section.
- Ordinary feedback updates the current working direction; it does not automatically become a durable rule.

## Workflow

1. Select Initialize Direction or Recover Baseline.
2. Identify product, audience, repeated job, density, references, constraints, dislikes, and anti-examples. State conservative inferences for missing evidence.
3. Read available UI, screenshots, prototypes, tokens, components, and project-native design docs. A personal-root `DESIGN.md` is long-term intent.
4. Identify the familiar surface type (content and reading, operational workflow, data exploration, or a spatial/relational canvas) and the components it actually needs (navigation, charts/tables/maps, forms/actions, legends, and status feedback). Preserve established component anatomy and interaction semantics where they serve the job; use project evidence for exact appearance. State one Design Read and three to five observable invariants; when an expert informed a choice, name its contribution. Ask at most one question only when the unresolved choice materially changes direction.
5. For authorized implementation or audit, use the Design Read as the baseline. Keep exact values in tokens and behavior in components/tests; audit-only requests report findings without editing.
6. When implementing or verifying the UI, read `rendered-verification.md` and inspect the relevant rendered surface. Correct drift only within authorized implementation scope; a direction-only discussion needs no browser run.
7. If the user asks to persist the accepted direction, follow `design-persistence.md`.

## Runtime Design Read

Use this compact shape and omit fields with no decision value:

```markdown
Design Read: <subject, audience, single job, and visual intent in one line>
Working invariants:
- <three to five observable constraints>
Expert input: <source and the decision it changed, only when used>
```

## Conservative Defaults

- Operational tools and dashboards: quiet, dense, scan-friendly, restrained color, predictable navigation, clear controls, and complete states.
- Content/editorial: readable typography, strong hierarchy, and restrained layout rhythm; do not invent a dashboard.
- Games, demos, and playful tools: expressive theme with explicit controls, states, and responsive framing.
- Unless requested, avoid one-note purple/blue gradients, beige/brown palettes, glassmorphism, oversized card grids, browser-default controls, decorative blobs, and generic marketing heroes.
