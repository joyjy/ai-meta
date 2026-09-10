# save-context: confirmed final-form state

Read only to preserve an existing confirmed final-form or write one explicitly requested by the user. Mainline/workstream protection remains in the main skill.

## ff Next Steps

Use an `ff` work order in Next Steps only when the user explicitly requested or confirmed a final-form, asked for a dispatchable work order / WorkItem, or an existing confirmed final-form must be preserved across sessions. Ordinary recovery notes remain plain-text Next Steps or `null`; do not promote unfinished Doing, candidate follow-ups, recurring automation, or a merely agent-executable action into final-form.

This is a compact v0 recovery contract, not a fully versioned final-form schema.
Keep machine-facing fields in context for dispatch, but do not require
human-facing load summaries to print them verbatim.

Use this compact object inside YAML `next_steps` or Markdown `Next Steps`:

```yaml
- ff:
    output_target: context
    goal: <one-sentence outcome>
    cwd: <absolute path, or null when not file-backed>
    scope:
      include: []
    acceptance: []
    blocking_questions: []
    ready_for_dispatch: true
    dispatch_target: symphony # codex | symphony | manual | unknown
```

Rules:

- `output_target: context` is required for new machine-facing `ff` blocks saved
  into context.
- The presence of enough detail to fill final-form fields is not authorization to create one. Without an explicit final-form / dispatch / WorkItem request or an existing confirmed final-form, save ordinary recovery state instead.
- When a user asks to save an `ff` into a named context abbr, existing and
  missing abbr paths are both valid:
  - Existing `~/.ai/contexts/<abbr>.md`: read it first, preserve unrelated
    mainline/workstream state, and update only the explicit route's next
    executable `ff`. Use `~/.ai/scripts/context-ff-merge` for this write.
  - Missing `~/.ai/contexts/<abbr>.md`: create a minimal `context.v3` snapshot
    with `mainline.state: active`, empty
    workstreams, and the generated `ff` in `mainline.next_steps`; use
    `~/.ai/scripts/context-ff-merge` for this write.
  - Invalid abbr names or a requested replacement of an unrelated active next
    step are blocking questions.
- `ready_for_dispatch: true` requires empty `blocking_questions`.
- `ready_for_dispatch: false` requires at least one blocking question.
- Omit empty `scope.exclude`, `checks`, `constraints`, `defaults`, `existing_capability_inventory`, `verification_loop`, and default `main_agent` parallelization. Preserve a non-default parallelization block when final-form produced one; absent means `main_agent`.
- Preserve a populated `automation_candidate` emitted by final-form, but never synthesize one during save or turn it into a separate context Next Step, dispatch authorization, or GTD task intent.
- Use `dispatch_target: symphony` only when `cwd`, `scope.include`,
  `acceptance`, and safety constraints are concrete enough for autonomous
  execution.
- Put non-blocking assumptions in `defaults`, not in `blocking_questions`.
- Do not move broad backlog themes into `ff`; narrow them to one inspectable
  action first.
