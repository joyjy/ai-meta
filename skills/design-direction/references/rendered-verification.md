# Rendered Verification

Run these stages in order. Complete each stage before starting the next.

1. **Render.** Capture the named existing UI or the implementation's first pass in the target runtime. If the user supplies only screenshots, review those views and state the coverage. For a runnable responsive web UI, capture one representative desktop and one mobile viewport unless the request narrows the scope. Use realistic content. Keep the same viewport, state, and content for the final comparison.
2. **Review with Taste Skill.** Apply the checks below and the applicable criteria from the checklist in `~/Documents/reference/taste-skill/skills/taste-skill/SKILL.md` ([upstream](https://github.com/Leonxlnx/taste-skill/blob/main/skills/taste-skill/SKILL.md) if absent). If the source is unavailable, disclose that the review used only the checks below. Do not apply Taste Skill's site template or edit during review. Finish with up to three visual findings, ordered by impact. Each finding names the viewport or state, the visible issue, and the expected result. Include user-reported defects and functional or accessibility blockers separately from the three findings. If the review finds nothing material, proceed to the report.
3. **Fix with Impeccable.** For each authorized finding, read the mapped command's Markdown file in `~/Documents/reference/impeccable/skill/reference/` ([upstream](https://github.com/pbakaus/impeccable/tree/main/skill/reference) if absent). Use `distill.md` for unnecessary copy or UI, `clarify.md` for unclear required copy, `layout.md` for composition or spacing, `typeset.md` for type hierarchy, and `polish.md` for other small visual defects. Apply the command's design guidance as a targeted edit within dd's scope. The reference checkout supplies guidance only. If the reference is unavailable, apply the same targeted edits directly and report the fallback. Preserve the accepted design direction and product behavior.
4. **Compare.** Render the changed view again with the same conditions. Check every finding against its expected result and inspect the visible copy. If a fix misses its expected result, make one targeted correction and check it again. Report any remaining issue or unavailable render explicitly.

When feedback includes a screenshot or a visual defect, inventory all visible material defects before choosing the edit. Treat an explicitly reported or recurring defect as a named acceptance condition: verify it after the edit in the same relevant viewport and interaction state using the rendered result, computed style, or geometry as appropriate. A matching source declaration such as `padding`, `gap`, or `width` is not evidence that the browser applied it.

Check:

- The first viewport shows the actual product, tool, or experience rather than an unrelated generic landing page.
- The primary task has the strongest visual emphasis. Check whether secondary panels, labels, or decoration compete with it.
- Check visual consistency even without a design contract. Compare elements with the same role across the views in scope. Look for competing type scales, spacing, colors, shapes, icon styles, or component treatments. If they lack a shared visual language, cite at least two concrete examples and name the rule they should share. Preserve distinctions that serve different roles or states. When an accepted reference exists, identify where the rendered UI diverges from it.
- Controls are recognizable and complete for the repeated workflow.
- Loading, empty, error, disabled, hover, focus, and selected states that exist in the surface are intentionally styled.
- Text and controls fit without overlap, clipping, or unusable density at the supported sizes.
- The result avoids anti-patterns named in the accepted direction or reference.
- Visible copy follows the Interface Copy rules. Look for headings followed by text that restates the heading, labels, or controls.

A review-only request stops after stage 2. If the target cannot render, review supplied screenshots when available and identify which views or states lack rendered evidence. Do not claim a visual pass without inspecting the target.
