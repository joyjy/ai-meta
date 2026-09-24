# Draft Fill

Use when the user wants the agent to prepare a complex web form and review it before manually committing the result.

## Preconditions

- The user has completed login and identified the intended page or tab.
- Resolve the form scope, requested outcome, supplied source material, and fields that remain business decisions.
- Inspect the form for autosave, validation-on-change, uploads, consent controls, payment, account changes, communication, and other effects that make editing consequential.

## Workflow

1. Snapshot the visible form and build an exact field-to-source mapping. Distinguish supplied facts, conservative transformations, and unresolved choices.
2. Fill only fields supported by the user's request or evidence. Do not invent identity, legal, financial, medical, employment, permission, or policy decisions.
3. Use field-level validation without pressing Enter or invoking form submission. Treat upload, consent, save-as-draft, and buttons that can mutate remote state according to their actual effect, not their label.
4. Re-read the rendered values and validation state. If the page navigates, autosaves, or loses the target, stop and report the observed effect; do not continue on a guessed replacement.
5. Leave the page at a reviewable state. Summarize filled fields, unresolved fields, validation warnings, and any values derived rather than copied.

## Hard Stop

Never activate the final submit, publish, send, confirm, purchase, delete, authorize, or equivalent commit action in this mode. A user request to fill the form does not authorize that action. The final action belongs to the user.

If an autonomous browser agent chooses actions, its output is advisory. The executor must enforce this stop independently of the model's labels or confidence.
