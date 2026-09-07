# save-context: context checkpoint and routing details

## Context Checkpoint Reminder

`save-context` is an explicit checkpoint for preserving recovery state before
task switching, pausing, or resuming later. Do not save silently; run it when the
user asks to save, pause, switch tasks, resume state, or record progress.

Do not proactively classify context risk. The user decides from the visible
context size whether a checkpoint is needed.

## Abbr And Script

Determine abbr in this order:

1. Explicit user input or slash-command argument.
2. Current directory `index.md` frontmatter `abbr:`.
3. Ask `请告诉我项目 abbr，例如：/save-context amt`, then stop.

Abbr may include `<abbr>:<workstream>`, for example
`amt:context-workstreams`.

Use only the fixed script for filesystem writes:

```bash
~/.ai/scripts/save-context <abbr> --context-stdin \
  --timeline "[HH:MM-HH:MM] <timeline text; script will prefix '- '>"
```

In Codex, use the same entry as a single checkpoint orchestrator:

```bash
~/.ai/scripts/save-context --orchestrate <abbr> \
  --admission-file <save-context.admission.v1.json> \
  --context-file <context-file> \
  --timeline "[HH:MM-HH:MM] <timeline text>"
```

Task title refresh is not a shell stage; after a successful context stage, use the client-native rename capability defined in `timeline-title-output.md`.

Before creating any output artifact, write a short admission file from current source-owner readback:

```json
{
  "schema": "save-context.admission.v1",
  "decision": "checkpoint_ready",
  "checked": [
    "gitlab:pipeline:792742=succeeded",
    "runtime:api:expected=running=294c0af"
  ],
  "actionable": []
}
```

Use `decision=continue_work` with at least one `actionable` item when a newly discovered failure, stale runtime, unfinished side effect, or other in-scope work can still be handled in the current task. The orchestrator then returns exit code 3 and `status=continue_work` without calling context/timeline or title helpers. `--pause-override` is valid only after the user sees that blocker and explicitly asks to pause/save anyway; the receipt records the admission as `overridden`.

The admission envelope is bounded to 16 KiB, at most 20 `checked` and 20 `actionable` entries, and 500 characters per entry. Store only source references and compact readback; never copy tokens, raw logs, or full artifacts into it.

The command emits one `save-context.checkpoint.v1` JSON receipt. Admission runs first, then a read-only context compile/validation preflight and context/timeline. Preflight failure preserves the helper's nonzero exit and skips every write stage. Formal context failure preserves the helper's nonzero exit. Native title rename happens only after the receipt proves the context stage succeeded. Repeated invocation keeps timeline idempotency in its owning helper.

Script rules:

- For `<abbr>`, the agent generates the complete context markdown. The helper validates that YAML `next_route` and the route-index `next=` field agree, then writes them as supplied. Preserve the existing recommendation unless the user explicitly changes the project summary; do not derive it from cwd, recent context, or an available workstream.
- For `<abbr>:<workstream>`, the agent passes a `context.workstream.v1`
  YAML/JSON payload. The script merges that route into the existing context and
  preserves mainline and unrelated workstreams.
- Normal non-Codex agent runs pass the selected input on stdin with
  `--context-stdin` when the client can provide stdin safely.
- Legacy calls without `--orchestrate` retain the existing `save_context.py`
  arguments, output, and exit codes.
- In Codex Desktop, use `--context-file <file>` for long input: write the
  complete context markdown or workstream payload to a temporary file under
  `/private/tmp`, call the fixed script with that file, then inspect the script
  output and context header. Long YAML has been observed to truncate through
  interactive TTY stdin.
- For short Codex input, `--context-stdin` through an interactive `tty: true`
  `exec_command` may work. Plain non-interactive `exec_command` can EOF stdin
  before content is sent.
- Empty or whitespace-only context input is rejected before writing. Use
  `--allow-empty` only when deliberately blanking a snapshot.
- `--validate-only` is the orchestrator's read-only preflight interface. It
  compiles and validates the same input, including the deterministic timeline
  date, without writing context or Daily Note files; direct checkpoint calls
  normally omit it.
- Non-empty input is validated before writing. Full context input must pass the
  context.v2 route-index/frontmatter/project checks; workstream input must pass
  the `context.workstream.v1` schema and field checks. The script writes by
  atomic replacement only after validation succeeds.
- Use `--context-file -` only for a client that can pipe stdin but cannot pass
  `--context-stdin`.
- Passing `<abbr>:<workstream>` performs a structural route merge. The payload
  must include `schema: context.workstream.v1`, `state`, `summary`, `doing`,
  `blocked`, `next_step`, and non-empty Markdown `details`. The script also
  updates `next_route`, `updated`, and the route index.
- Use `--date YYYY-MM-DD` when the deterministic timeline checkpoint belongs to
  a non-current local date.
- Use `--skip-timeline` or omit `--timeline` when there is no substantive Daily
  Note entry.
- Use `--timeline-only --timeline "<...>"` and omit context input when only
  appending a Daily Note entry.
- For confirmed workstream closure, rewrite `~/.ai/contexts/<abbr>.md` without
  that workstream after durable sync. Do not use `--delete-context` for one
  workstream in context.v2.

Workstream payload example:

```yaml
schema: context.workstream.v1
state: active
summary: One-line recovery summary
doing:
  - Current unfinished work
blocked: []
next_step: First concrete resume action
details: |
  ### Constraints & Preferences

  - （无）

  ### Doing

  - Current unfinished work

  ### Blocked

  - （无）
```

Write it with:

```bash
~/.ai/scripts/save-context amt:forum \
  --context-file /private/tmp/forum.yaml --skip-timeline
```

Offline recovery:

- If the source Codex thread is too long, stuck, or already interrupted before
  `save-context` can complete, do not resume that same thread just to save.
- In a fresh thread, run
  `~/.ai/scripts/save-context-recover
  --thread-id <id>` or `--rollout <jsonl>` to extract a compact recovery packet
  from `~/.codex/sessions` / `~/.codex/archived_sessions`.
- Treat the packet as evidence, not as the context itself. The agent still
  writes a clean context.v2 snapshot with the fixed `save-context` script.

## Route Mainline Vs Workstream

Context files are recovery snapshots, not durable knowledge. Keep one project
context file per abbr:

- Project context: `~/.ai/contexts/<abbr>.md`
- Legacy workstream context: `~/.ai/contexts/<abbr>/<workstream>.md` may exist
  from older saves; do not create new files there.

Definitions:

- Mainline: project-level summary used by `load-context <abbr>` and dashboards.
- Workstream: unfinished, independently recoverable project-local work whose
  Doing / Next Step should not overwrite mainline.
- Completed small task: result already synchronized to durable layers and no
  independent Next Step remains.

Routing rules:

- A bare `<abbr>` targets mainline; explicit `<abbr>:<workstream>` targets that
  workstream. Do not split a workstream
  merely because a save includes several files, several topics, or a completed
  slice with no independent recovery need.
- Explicit `<abbr>:<workstream>` updates that workstream inside the project
  context unless closure is confirmed.
- When no route was explicitly supplied, a session that clearly continues an
  existing workstream may update it; explicit user input always wins.
- Create a new workstream only when the user names one, the task has a durable
  project-local identity and a concrete unfinished Next Step, and writing it to
  mainline would overwrite or confuse unrelated mainline recovery state.
- Completed small tasks do not create workstreams; update durable layers and
  append a timeline entry when substantive.
- Explicit project summary, handoff, or promote operation updates mainline.
- If multiple routes are plausible, ask one short question before writing.

Non-destructive save rules:

- Do not overwrite context just to append a timeline after a quick task.
- Read existing target context before writing and compare recovery state.
- Start repeat saves from the last saved route / Doing / Blocked / Next Steps /
  Critical Context; avoid duplicate timeline entries.
- Rewrite context only when recovery state materially changes: Doing, Blocked,
  Next Steps, route, workstream state, closure decision, or critical recovery
  facts.
- If context rewrite is skipped, say so in the final `临时状态层`.

Workstream naming and protection:

- Use human-readable slugs such as `context-format` or `agent-doc-hygiene`.
- Prefer existing matching workstreams; avoid near-duplicates.
- Do not use timestamp-only names unless requested.
- Do not create top-level aliases such as `amt-context-format.md`.
- Preserve unrelated active workstreams when updating mainline.

Closure:

- `save-context` is the normal closure check trigger. Phrases such as "做完了",
  "可以了", "收束一下", "promote", or "合到主线" also trigger checking.
- A workstream is a closure candidate when Doing is complete or empty, remaining
  Next Step is empty or already moved to durable layers / mainline / backlog,
  and important results are synchronized.
- If abandoned or parked, mark `parked` when it still has recovery value; remove
  only after user confirms it no longer needs recovery.
- Never silently close, promote, or delete an ordinary or ambiguous workstream
  entry or detail section.
- A proven completed exact context-backed final-form is a narrow exception. When the
  current session directly proves the final-form goal, acceptance, required checks,
  and authorized exit actions completed, use `~/.ai/scripts/context-ff-merge
  <abbr[:workstream]> --clear-completed --expect-goal '<exact ff.goal>'`.
  The helper clears only the exact match and removes the workstream plus its
  Markdown detail only when no other Doing or Blocked recovery state remains.
  Do not retain that empty route as `idle` or `closure-candidate`.
- Recommend "close" when there is no independent Next Step; recommend "keep"
  when a concrete Next Step remains.
- Confirmed closure first completes durable sync, then removes YAML and Markdown
  detail for ordinary workstreams. The exact completed-final-form exception above does
  not require a second closure confirmation.

## Context.v2 Template

```markdown
---
# context: project=<abbr>; mainline=<idle|active|blocked>; workstreams=<count>(<state:name, state:name>); next=<mainline|workstream-name|none>
schema: context.v2
project: <abbr>
goal: <one-sentence project goal>
mainline:
  state: idle | active | blocked
  summary: <short mainline recovery summary, or null>
  doing: []
  blocked: []
  next_steps: []
workstreams:
  <workstream-name>:
    state: active | parked | blocked | closure-candidate
    summary: <one-line recovery summary>
    doing: []
    blocked: []
    next_step: <first concrete next action, or null>
next_route: <mainline|workstream-name|null>
updated: <YYYY-MM-DD>
---

# <project or route title>

## Mainline

<use the route section schema below>

## Workstreams

### <workstream-name>

<use the route section schema below>
```

Route section schema:

- `Constraints & Preferences`: session-specific exceptions, or `- （无）`.
- `Doing`: current active work, or `- （无）`.
- `Blocked`: blockers and reasons, or `- （无）`.
- `Key Decisions`: only decisions not yet durable, or durable references.
- `Next Steps`: concrete, verifiable resume actions; if none, `- （无）`.
- `Critical Context`: recovery anchors such as paths, IDs, tools, URLs, temp
  cleanup state, worktrees, and commit deferrals.
- `Relevant Files`: short list of files to open first, with why.

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
  - Missing `~/.ai/contexts/<abbr>.md`: create a minimal `context.v2` snapshot
    with `next_route: mainline`, `mainline.state: active`, empty
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

Snapshot rules:

- First line is mandatory and must reveal project, mainline state, workstream
  count/status, and recommended next route.
- YAML stays thin and parseable; long analysis belongs nowhere in context unless
  it is unfinished investigation state that cannot be reconstructed.
- YAML `workstreams` is the authoritative list of active / parked / blocked /
  closure-candidate workstreams.
- `next_route` is a recommendation for project summaries and route indexes, not
  routing authority; explicit user input always wins.
- Move completed Doing and resolved Blocked out of recovery snapshots.
- If there are no blockers, write exactly `- （无）` under `Blocked`.
- Keep Constraints, Key Decisions, Critical Context, and Relevant Files short.
- Prefix context-only durable decisions with `pending durable home:`.
- Next Steps must be concrete, verifiable resume actions; do not invent fallback
  guidance.
- A valid Next Step names the immediate action and its completion check, so the
  next agent can tell whether it is done from a file diff, command output,
  reviewed artifact, linked issue/MR state, or explicit user confirmation.
- Do not copy broad backlog items, strategy themes, or "align/design/research"
  directions into Next Steps unless they are narrowed to one inspectable slice
  with a clear output, such as a specific contract table, API comparison note,
  failing/passing command, or updated file.
- Preserve exact paths, issue/MR links, local URLs, script names, skill/tool
  entrypoints, and "use this tool next" notes needed for recovery.
- Use absolute dates; avoid "today" or "recently".
- Do not rewrite unchanged recovery state just to summarize completed work.
