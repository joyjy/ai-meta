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

## Self-Check

Before final output, confirm:

- Mentioned paths, symlinks, commands, and entrypoints exist.
- `index.md` backlog matches completed/current work.
- Context starts with standard YAML frontmatter; its second-line route index exists and matches YAML.
- Context route is explicit and does not leave completed work in Doing.
- Context has no invented fallback Next Step when no concrete action exists.
- Context does not repeat durable rules, architecture, backlog history, or skill
  instructions.
- Recovery-critical paths, commands, URLs, tool names, and "use this next" notes
  are preserved.
- YAML is thin; Markdown detail is only for active unfinished recovery state.
- Context was not rewritten when only Daily Note or durable sync was needed.
- Daily Note includes only substantive human-facing progress.
- Daily Note boundaries came from `save-context-timeline`; they describe
  checkpoint coverage rather than net work time.
- Active workstreams were not silently promoted, closed, or deleted.
- Closure candidates were confirmed before deletion.
- Commit decision was handled, and deferred commits are not default Next Steps.
- Context uses absolute dates.
- `instructions.md` did not receive project-specific content.
- Agent frictions were recorded or intentionally skipped as one-off/noise.
- Team/external `AGENTS.md` did not receive private/local/personal content.
- ADRs and convention-level decisions were written to the correct layer.
- Codex native task title refresh ran or skip/failure is reported.

## Output

After saving, summarize:

```markdown
## 同步完成

### 全局偏好层（instructions.md）
- 无变更 / <具体改动>

### 项目架构层（AGENTS.md）
- 无变更 / <具体改动>

### 默认工具入口层
- 无变更 / recorded: <route title> / updated: <route title>

### Agent 运行摩擦层
- 无变更 / recorded: <friction title> / updated: <friction title> / skipped: <原因>
- 独立 agent 审计：frictions <N>；prompt/contract gaps <N>；promoted <N> / resolved <N> / ignored <N> / deferred <N> / skipped（<原因>）
- 摩擦结算：promoted <N> / resolved <N> / ignored <N> / deferred <N> / 无
- 产物 / 补证条件：<promoted 对应 durable entry 或 final-form；deferred 对应缺失证据与重试条件；无则省略>

### 任务文档层
- index.md：<具体改动>
- ADR：<追加 ADR-00N 标题 / 无> 或 decisions.md：<追加标题 / 无>

### 临时状态层
- route: mainline `contexts/<abbr>.md` / workstream `<abbr>:<workstream>` in `contexts/<abbr>.md` / closed `<abbr>:<workstream>` / skipped（timeline-only，未改动 context）
- Doing: <内容>
- Blocked: <内容 / （无）>
- Next Steps: <第一条 / （无）>
- closure: 无 / 已询问并保留 / 已确认收束并删除快照

### Daily Note
- appended: <一句话摘要> / 跳过（无实质内容）

### Git Commit 决策
- 无需 commit / 已 commit：`<message>` / 用户确认暂缓：<原因> / 未处理：建议 `<message>`

### Codex Task
- title refresh: `<old> -> <new>` / 当前标题未变化（已符合规则）
- title refresh: 跳过：<原因>
- title refresh: 失败：<原因>

### 待确认
- <建议新建 decision 但未创建的，列在这里>
- <其他需要用户决定的事项>
```

When `save-context` completes and returns the final report, the last
user-facing sentence must be:

```markdown
保存完成了，站起来活动一下身体，上个厕所喝点水。
```
