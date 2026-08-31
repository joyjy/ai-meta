---
name: design-direction
description: Establish or recover a design direction for HTML, pages, demos, dashboards, tools, or UI-heavy features. Use when the user says dd, before new UI work, substantial visual redesign, or when an existing UI starts drifting with feedback such as "开始乱搞", "风格跑偏", "保持现在这个感觉", "别换风格", or "先锁一下设计".
---

# design-direction

Use before new UI work, major redesign, or when an acceptable UI drifts. Skip tiny fixes in a clear design system. State compact Design Read, then implement or audit and verify; project evidence is primary.

## Modes

- **Initialize Direction**: new UI, substantial redesign, or no clear design contract. Ask what the surface should become.
- **Recover Baseline**: an acceptable UI is drifting, or the user asks to preserve its current feel. Infer what already works from its layout, density, type, color, component, control, and state language.

In recovery, preserve the existing language. Switch modes only when the user asks to change the overall style. Persistence is a gate, not a third mode.

## Conditional References

- When a specialist lens would materially improve direction selection, read at most one directly from `~/Documents/reference/taste-skill/skills/`: `taste-skill/SKILL.md` for brand-heavy pages, `redesign-skill/SKILL.md` for audit-first correction, or `minimalist-skill/SKILL.md` for restrained tools and dashboards. If that optional reference checkout is absent, continue from project evidence without searching for another copy.
- Read `references/rendered-verification.md` when implementing or verifying the UI.
- Read `references/design-persistence.md` only after the user explicitly asks to lock or save the accepted direction.

Load only triggered direct references; local references do not route onward.

## Safety And Ownership

- `DESIGN.md` persistence requires explicit lock/save intent, a compact proposed contract, and user confirmation.
- Personal `DESIGN.md` belongs only at the personal project root that owns `index.md`; never infer cwd or a team/external source repo as a fallback.
- Project-native design docs in team/source repos are read-only evidence unless the user separately authorizes editing them.
- Never replace a design document wholesale. Preserve unrelated content and patch only the confirmed section.
- Ordinary feedback updates the current working direction; it does not automatically become a durable rule.

## Workflow

1. Select Initialize Direction or Recover Baseline.
2. Identify product, audience, repeated job, density, references, constraints, dislikes, and anti-examples. State conservative inferences for missing evidence.
3. Read available UI, screenshots, prototypes, tokens, components, and project-native design docs. A personal-root `DESIGN.md` is long-term intent.
4. State one Design Read and three to five observable invariants. Ask at most one question only when the unresolved choice materially changes direction.
5. Implement or audit against it. Keep exact values in tokens and behavior in components/tests.
6. Read `rendered-verification.md`, inspect desktop and mobile output preferably in a browser, and correct material drift before reporting done.
7. If the user asks to persist the accepted direction, follow `design-persistence.md`.

## Runtime Design Read

Use this compact shape and omit fields with no decision value:

```markdown
Design Read: <subject, audience, single job, and visual intent in one line>
Working invariants:
- <three to five observable constraints>
```

## Conservative Defaults

- Operational tools and dashboards: quiet, dense, scan-friendly, restrained color, predictable navigation, clear controls, and complete states.
- Content/editorial: readable typography, strong hierarchy, and restrained layout rhythm; do not invent a dashboard.
- Games, demos, and playful tools: expressive theme with explicit controls, states, and responsive framing.
- Unless requested, avoid one-note purple/blue gradients, beige/brown palettes, glassmorphism, oversized card grids, browser-default controls, decorative blobs, and generic marketing heroes.
