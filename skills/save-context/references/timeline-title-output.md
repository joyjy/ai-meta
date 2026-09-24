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

## Historical Title Maintenance

普通 current-task title refresh 与最终输出由主 skill 自包含。本节只在用户明确要求历史/批量维护时使用：

- 通过原生 list/read 解析 exact task IDs，并逐个用原生 rename；不要按最新时间选择，也不要直接写 Codex SQLite/index 或运行 `codex_session_titles.py`。
- 从 source identity 与 execution context 排除 automation，不因短标题推断。
- 原生能力无法重命名 archived task 时，可临时 unarchive exact task、rename、恢复 archived state，并回读两项；不得遗留 archive side effect。
- 缺少能力或失败时报告 exact skip/failure，不回退到本地数据库写入。
