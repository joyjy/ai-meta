# save-context: context schemas

仅在新建或修复完整 context.v3 / workstream payload 时读取。

## Workstream Payload

传给 `<abbr>:<workstream>` 的文件必须包含：

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

Fixed writer 会校验并把该 route 合并进现有 context，更新 `updated` 与 route index，同时保留 mainline 和其他 workstream。

## Context.v3

```markdown
---
# context: project=<abbr>; mainline=<idle|active|blocked>; workstreams=<count>(<state:name, state:name>)
schema: context.v3
project: <abbr>
goal: <one-sentence project goal>
mainline:
  state: idle | active | blocked
  summary: <short summary, or null>
  doing: []
  blocked: []
  next_steps: []
workstreams:
  <workstream-name>:
    state: active | parked | blocked | closure-candidate
    summary: <one-line summary>
    doing: []
    blocked: []
    next_step: <first concrete action, or null>
updated: <YYYY-MM-DD>
---

# <project or route title>

## Mainline

<route section>

## Workstreams

### <workstream-name>

<route section>
```

每个 route section 依次使用 `Constraints & Preferences`、`Doing`、`Blocked`、`Key Decisions`、`Next Steps`、`Critical Context`、`Relevant Files`；正文 section 为空时写 `- （无）`。

## Invariants

- 第一行是 `---`；第二行 route-index comment 必须与 YAML project/mainline/workstreams 一致。YAML 是 authoritative route list，保持薄且可解析。
- 只保留 unfinished recovery state。完成的 Doing、已解除的 Blocked 和已有 durable home 的结论移出 context；暂时没有 owner 的决定前缀为 `pending durable home:`。
- Next Step 必须是可验证的立即动作，并说明可由 diff、命令输出、artifact、issue/MR 状态或用户确认判断完成；不要放宽泛 backlog、战略主题或未收敛的“对齐/设计/研究”。
- 保留恢复所需的 exact paths、IDs、issue/MR links、local URLs、script/skill/tool entrypoints、worktrees、generated outputs、临时清理与 commit deferral；其余分析不进 snapshot。
- 使用绝对日期；不要为总结已完成工作而重写不变的 recovery state。
