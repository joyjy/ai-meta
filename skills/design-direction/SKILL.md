---
name: design-direction
description: Set visual direction for new UI or a redesign, critique an existing interface, or save an accepted direction. Use for dd, 界面找毛病, 风格跑偏, or 先锁一下设计.
---

# design-direction

Use before new UI work, major redesign, or when an acceptable UI drifts. Skip tiny fixes in a clear design system. Continue implementation only when the user's request already authorizes it.

## Review an Existing UI

Requests such as `dd 找毛病`, `dd review`, `dd 只评审`, or reports of visual drift take the review path for an existing UI. Use the page, component, or screenshot identified by the request or conversation. Ask for the target only when it cannot be identified.

Go directly to stages 1 and 2 of [Rendered Verification](references/rendered-verification.md). Use an accepted design contract or reference when available. Use the current interface to check internal consistency and infer the screen's primary job. Skip the Design Read, direction selection, and specialist routing. Report the findings and stop. Continue to stages 3 and 4 only if the user also asks to fix the findings.

## Conditional References

- Use project evidence to set visual direction. Use an outside visual reference at this stage only when the user requests it or the project already names it. Record the design choice it changed.
- Complex workflow, dashboard, chart, or graph interaction → `~/Documents/reference/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md` ([upstream](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md) if absent); use only the applicable UX or chart guidance.
- UI worst-case testing, or a concrete concern about long text, missing fields, counts, or collection size → `~/Documents/reference/skill-ref-emil/skills/break-ui/SKILL.md` as the data-robustness expert. Read its field-boundary, fixture, rendered-check, and reporting workflow; load its `CATALOG.md` only to select applicable cases. Apply the diagnostic method within the current audit/implementation authority: derive plausible inputs from actual contracts, inject through the data boundary, and inspect the rendered result. Use project-native fixtures or previews; do not require a permanent toggle or import the expert's separate approval flow. Ordinary visual-direction work does not load this expert.
- For an interactive information graphic or network map with overview, focus, or zoom decisions, read `patterns/information-graphic-navigation.md` and apply only the conditions that match the surface.
- Read [Rendered Verification](references/rendered-verification.md) before implementing or auditing the UI. It defines the Taste Skill review and Impeccable fix passes.
- Read `references/design-persistence.md` only after the user explicitly asks to lock or save the accepted direction.

Load only triggered direct references. Local references do not route onward, except Rendered Verification's Taste Skill review and Impeccable fix passes.

## Safety And Ownership

- `DESIGN.md` persistence requires explicit lock/save intent and confirmation of the compact proposed contract; a request to save an already displayed and accepted contract supplies that confirmation.
- Personal `DESIGN.md` belongs only at the personal project root that owns `index.md`; never infer cwd or a team/external source repo as a fallback.
- Project-native design docs in team/source repos are read-only evidence unless the user separately authorizes editing them.
- Never replace a design document wholesale. Preserve unrelated content and patch only the confirmed section.
- Ordinary feedback updates the current working direction; it does not automatically become a durable rule.

## Workflow

1. For new UI or a redesign, identify product, audience, repeated job, density, references, constraints, dislikes, and anti-examples. State conservative inferences for missing evidence.
2. Read available UI, screenshots, prototypes, tokens, components, and project-native design docs. A personal-root `DESIGN.md` is long-term intent.
3. Identify the familiar surface type (content and reading, operational workflow, data exploration, or a spatial/relational canvas) and the components it actually needs (navigation, charts/tables/maps, forms/actions, legends, and status feedback). Preserve established component anatomy and interaction semantics where they serve the job; use project evidence for exact appearance. State one Design Read and three to five observable invariants; when an expert informed a choice, name its contribution. Ask at most one question only when the unresolved choice materially changes direction.
4. Direction-only work ends after the Design Read. For implementation, follow the fixed sequence in Rendered Verification: **render the first pass → review with Taste Skill → fix with Impeccable → compare the renders**. Keep exact values in tokens and behavior in components/tests.
5. If the user asks to persist the accepted direction, follow `design-persistence.md`.

## Runtime Design Read

Use this compact shape and omit fields with no decision value:

```markdown
Design Read: <subject, audience, single job, and visual intent in one line>
Working invariants:
- <three to five observable constraints>
Expert input: <source and the decision it changed, only when used>
```

## Interface Copy

- Apply this to the first pass: omit decorative labels above headings. Leave the space below headings free of explanatory copy by default. Use grouping, hierarchy, and clear action labels to convey purpose. Preserve necessary product copy and business status.
- For optional supplementary detail, prefer an accessible info control with a tooltip or popover over persistent helper text. Make it available by keyboard and touch; keep essential instructions, errors, and decision-critical information visible rather than hiding them there.
- Preserve necessary form labels and accessible names for assistive technology. Keep clear consequence information for dangerous or irreversible actions, including deletion, payment, and permanent submissions.
- When simplifying an existing UI, remove redundant copy first, then improve grouping, hierarchy, spacing, and action labels if clarity drops. Verify that a first-time user can still tell where to act next and what that action will do; retain concise visible guidance where structure and labels are insufficient.

## Conservative Defaults

- Operational tools and dashboards: quiet, dense, scan-friendly, restrained color, predictable navigation, clear controls, and complete states.
- Content/editorial: readable typography, strong hierarchy, and restrained layout rhythm; do not invent a dashboard.
- Games, demos, and playful tools: expressive theme with explicit controls, states, and responsive framing.
- Unless requested, avoid one-note purple/blue gradients, beige/brown palettes, glassmorphism, oversized card grids, browser-default controls, decorative blobs, and generic marketing heroes.
