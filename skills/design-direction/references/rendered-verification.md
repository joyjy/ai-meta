# Rendered Verification

Verify the rendered surface, preferably in a browser, at representative sizes supported by the target; for responsive web UI include desktop and mobile. Cover only relevant dimensions: hierarchy, density, layout, color and typography roles, component language, interaction states, responsive behavior, accessibility, and the direction's named anti-patterns.

When feedback includes a screenshot or a visual defect, inventory all visible material defects before choosing the edit. Treat an explicitly reported or recurring defect as a named acceptance condition: verify it after the edit in the same relevant viewport and interaction state using the rendered result, computed style, or geometry as appropriate. A matching source declaration such as `padding`, `gap`, or `width` is not evidence that the browser applied it.

Check:

- The first viewport shows the actual product, tool, or experience rather than an unrelated generic landing page.
- Spacing, typography, borders, radii, shadows, colors, and icon language follow the Design Read and invariants.
- Controls are recognizable and complete for the repeated workflow.
- Loading, empty, error, disabled, hover, focus, and selected states that exist in the surface are intentionally styled.
- Text and controls fit without overlap, clipping, or unusable density at the supported sizes.
- The result avoids anti-patterns named in the direction or recovered baseline.

For authorized implementation, correct material failures before reporting done. For audit-only work, report findings without edits. If rendering cannot be inspected, disclose the unverified surface; do not claim a visual pass. Stop after relevant checks pass unless new changes or failures justify another pass. Exact visual values belong in tokens; exact interaction behavior belongs in components or tests.
