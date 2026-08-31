# Rendered Verification

Verify the rendered surface, preferably in a browser, at representative desktop and mobile sizes. Cover only relevant dimensions: hierarchy, density, layout, color and typography roles, component language, interaction states, responsive behavior, accessibility, and the direction's named anti-patterns.

Check:

- The first viewport shows the actual product, tool, or experience rather than an unrelated generic landing page.
- Spacing, typography, borders, radii, shadows, colors, and icon language follow the Design Read and invariants.
- Controls are recognizable and complete for the repeated workflow.
- Loading, empty, error, disabled, hover, focus, and selected states that exist in the surface are intentionally styled.
- Text and controls fit without overlap, clipping, or unusable density at desktop and mobile sizes.
- The result avoids anti-patterns named in the direction or recovered baseline.

Correct material failures before reporting done. Exact visual values belong in tokens; exact interaction behavior belongs in components or tests.
