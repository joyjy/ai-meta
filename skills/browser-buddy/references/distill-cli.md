# Distill CLI

Use when a browser workflow is difficult or repetitive and the user wants to determine whether its stable semantics can be exposed through a connector, API, CLI, browser-context helper, or repeatable browser test.

An explicit request to watch the user's change and capture its interface selects live network observation. Bind the exact tab, start a bounded capture before the demonstrated action, report that capture is ready, let the authorized actor perform the action, then stop and inspect the relevant requests. Existing APIs, CLIs, frontend bundles, or source code provide baseline, readback, and gap-filling evidence after the live capture; they do not replace the requested observation.

## Capture Boundary

- The user completes login. Do not extract, print, persist, or reuse passwords, one-time codes, browser cookies, authorization headers, CSRF tokens, or equivalent session secrets as a new authentication mechanism.
- Bind one exact tab and a bounded capture interval. State whether the user or the agent will perform the demonstration and apply that mode's authority rules.
- Capture the minimum useful evidence: method, normalized URL, initiator, request shape, response status/media type/schema, timing, and the user action that caused it. Filter static assets, telemetry, and unrelated polling unless they explain the workflow.
- Write raw or detailed evidence to a task-specific temporary file before summarizing. Redact secrets and personal data before retaining or sharing it.

## Analysis

For each candidate interface, determine:

- owner and whether an official connector, API, SDK, or CLI already exists;
- authentication model without exporting the browser session;
- request and response schema, pagination, rate limits, errors, versioning, and idempotency;
- whether success has an independent readback;
- whether replay is read-only, reversible, or externally mutating.

Do not treat the existence of an XHR, GraphQL operation, or internal endpoint as proof of a supported reusable contract.

## Result Classes

- **Stable service interface**: prefer the official owner entry and implement or propose a CLI/connector around it.
- **Stable semantics but browser-session-only transport**: keep a narrow browser-context helper; do not export session credentials or claim it is an independent CLI.
- **UI-coupled repeatable workflow**: make it a project-owned Playwright/golden flow.
- **Unstable or unclear contract**: preserve the evidence and gaps; do not automate replay.

Never replay a mutating request merely to prove it works. Existing authorization to observe or draft does not authorize external writes.

## Deliverable

Return a compact inventory containing trigger action, method and normalized endpoint, request fields, response fields, authentication category, effect/idempotency, readback, confidence, and recommended owner layer. Include exact evidence paths and cleanup state.
