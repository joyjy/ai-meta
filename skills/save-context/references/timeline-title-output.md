# save-context: timeline, title, self-check, and output details

## Daily Note Timeline

Role:

- Daily Note is a thin human work log, not the recovery source of truth.
- Client logs are the raw transcript layer.
- Context snapshots remain the recovery index; do not put active Doing /
  Blocked / Next Steps in Daily Note unless it is a one-off human-facing note.

Append a timeline entry when the session produced substantive work:

- durable file changes, commit, push, MR, issue, document, ADR, or backlog
  update;
- accepted decision or preference with lasting effect;
- investigation result, diagnosis, or blocker the user may look for later;
- workstream closure, handoff, or meaningful phase transition.

Skip when the session only loaded context, refreshed a Codex title, checked
status, answered a narrow question, rewrote only a context snapshot, or did
mechanical routing / permission / setup checks recoverable elsewhere.

When ambiguous, ask briefly or choose `--skip-timeline` for low-value noise.
Entries are one compact line:

```text
[HH:MM-HH:MM] <what changed or what was learned>
```

Use links or file paths when useful. For Codex, first run one of:

```bash
~/.ai/scripts/save-context-timeline \
  --thread-id <codex thread id>
```

```bash
~/.ai/scripts/save-context-timeline \
  --rollout <rollout.jsonl>
```

The JSON contract is:

- `thread_id`: exact Codex thread.
- `timezone`: current local timezone used for every output timestamp.
- `first_user_at`: first included deduplicated `role=user` message after the
  control-only exclusion below.
- `last_user_at`: last included deduplicated `role=user` message.
- `user_message_count`: number of included deduplicated user turns.
- `excluded_control_turn_count`: number of command-only `load-context` turns
  excluded from checkpoint boundaries.
- `checkpoints`: one entry per local calendar date, containing that date and its
  latest user timestamp.
- `checkpoint_at`: objective checkpoint boundary; currently equal to
  `last_user_at`.

The default summary omits individual timestamps. Use `--include-points` only
when diagnosing parser, deduplication, or rollout-schema behavior; it adds
chronological `user_points` with `turn_id` when available.

Exclude a turn only when its user-authored content is solely `/load-context`,
`$load-context`, or the equivalent skill link plus an optional abbr; known
client-injected skill/environment blocks in the same turn do not make it
substantive. If the same turn contains any additional user request, include it.
Never infer exclusion from elapsed time or later tool activity.

Use `first_user_at` and `checkpoint_at` for a single-date displayed range. Never
inspect assistant messages, tool activity, tests, commits, file changes, or
Daily Notes to infer a different start/end. Do not classify activity, build
clusters, estimate intensity, subtract pauses, or recommend a narrower range.

The range means “this conversation checkpoint covers user interaction from the
first boundary to the last boundary.” It does not claim continuous activity,
precise net work time, or an effective-work interval.

Use the local date in `checkpoint_at` as the Daily Note date and pass
`--date <YYYY-MM-DD>` when it is not today. If `checkpoints` contains multiple
dates, preserve each date's latest checkpoint instead of collapsing everything
to the newest date. This is a deterministic calendar partition, not an activity
range; do not apply the previous 09:00 cutoff or invent overnight clusters.

## Codex Task Title Refresh

After `save-context.checkpoint.v1` reports a successful context stage, refresh the current task through the client's native task-title or rename capability. In Codex Desktop, call the native `set_thread_title` tool with the exact current task ID. Do not edit `~/.codex/state_5.sqlite`, `session_index.jsonl`, or other client databases/indexes directly, and do not run `codex_session_titles.py` as a write path.

Rules:

- Non-blocking.
- Refresh only the exact current task; never select it by newest timestamp.
- Preserve the established `[abbr][MMdd] <summary>` shape. Use the explicit save-context route for `abbr` and the checkpoint's local date for `MMdd`.
- Derive `<summary>` from the primary substantive user goal. Ignore control-only `load-context`, `engineering-exit`, and `save-context` invocations plus injected skill/environment blocks; do not reduce the title to a workflow stage.
- A Daily Note entry may supply concise wording, but it does not override the substantive goal when it only describes a checkpoint or handoff.
- Keep an already specific and accurate title when observable; otherwise prefer the user's language and a distinctive outcome-oriented summary.
- Historical maintenance is explicit-only. Inventory tasks through native list/read capabilities, exclude automation from source identity and execution context, then rename exact task IDs one at a time through the native tool. Do not infer automation solely from a short title.
- If the native tool cannot rename an archived task, temporarily unarchive that exact task, rename it, restore its archived state, and verify both fields. Never leave archival state changed as a title-maintenance side effect.
- Capture output and include `title refresh: <old> -> <new>` or
  `title refresh: 当前标题未变化（已符合规则）`.
- If the native capability is missing or fails, report the exact skip/failure reason under `待确认`; do not fall back to local database writes.

## Self-Check And Output

Check the receipt and changed surfaces: route identity, preserved unrelated workstreams and recovery anchors, thin YAML/Markdown, correct owner for durable facts, deterministic timeline dates, Git decision when relevant, and native title outcome. Do not rescan unchanged layers or turn advisory gaps into new Next Steps.

Lead with saved / partially saved / blocked and the exact output paths. Report only changed layers, unresolved blockers, and the immediate recovery entry. Omit unchanged-layer headings and empty checklists. Always report title refresh as changed, unchanged, skipped (reason), or failed (reason); report Git actions only when applicable. For friction settlement, include counts and the durable destination or missing evidence. Do not describe `continue_work` as saved.

When `save-context` completes and returns the final report, the last
user-facing sentence must be:

```markdown
保存完成了，站起来活动一下身体，上个厕所喝点水。
```
