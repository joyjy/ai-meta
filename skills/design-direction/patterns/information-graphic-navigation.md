# Information Graphic Navigation

Use when an interactive information graphic, graph, or network map presents a larger data scope through overview, focus, search, or zoom. A static chart or small diagram without navigation does not need canvas controls.

## Forces

- Showing every item at equal emphasis can make a dense view unreadable.
- Showing only a selected subset can make an overview falsely appear complete.
- Zoom and focus help inspection but can leave users unsure where they are or how to return.

## Pattern

- Identify the full data scope before choosing an overview. A view labeled global preserves the complete scope; if it samples or filters, label that limitation explicitly.
- Improve readability through visual emphasis, search, and focus states instead of silently dropping items.
- Define the route between overview and detail. For a pannable canvas, choose fit, reset, or native-scale shortcuts when they serve the reading task; bound zoom to useful scales and keep controls consistent across views.
- Explain non-obvious node, edge, color, and selection encodings in the visualization itself.
- When the interaction pattern is uncertain, consult current primary visualization and accessibility guidance before fixing the direction.
