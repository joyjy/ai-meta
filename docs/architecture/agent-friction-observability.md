---
type: Reference
title: Agent run audit and friction observability
description: Independent prompt and execution audit plus objective Codex event ownership, settlement, and retention boundaries.
resource:
tags: [ai-meta, architecture, agent-ll, observability]
---

# Agent Run Audit And Friction Observability

## Scope

本 shard 记录 agent run 独立语义审计与执行摩擦观测的当前能力边界。它一方面比较用户意图、
生成契约、实际执行和后续纠正，另一方面采集可复算的 Codex runtime metadata，让
`/save-context`、`load-context` 和 loop-ledger 共享同一套事件与 ownership。它不做实现质量或通用性能
评分，也不是通用遥测平台。

## Current Facts

稳定入口是 `~/.ai/scripts/agent-frictions`，源文件为 repo `scripts/agent-frictions` 与
`scripts/agent_frictions.py`。v0 支持：

- `collect`：读取 Codex active / archived rollout JSONL，只消费 `session_meta`、
  `turn_aborted` 和 `patch_apply_end` 的结构化 metadata；
- `checkpoint`：把明确选择的 event IDs 归属 exact loop-ledger contract 或 stable context route；
- `claim`：把一个 exact context route 的 events 原子转移给 exact loop-ledger contract，并保留
  `claimed_from`；
- `list`：按 owner、lifecycle 和 exact `source-id` / `thread-id` 查询安全摘要；
- `status`：只返回指定 owner 的 actionable count 及 lifecycle / event-type 计数，供 save/load 提醒，不展开 facts；其中 actionable 仅包含 `pending` / `claimed`，`deferred` 仍保留在 lifecycle 统计中但不触发待处理提示；
- `settle`：要求 exact expected owner 和显式 resolution，将候选标记为 `promoted`、
  `resolved`、`ignored` 或 `deferred`，settled events 写月度 JSONL rollup；
- `record-occurrence`：消费已结算 audit 中由 receipt 派生的 exact thread/project identity，在 Agent 已完成 signature 归并后幂等更新对应 durable entry；同一 signature 的多 lane 只形成一个 occurrence，新条目首次登记需要显式 `--initialize`，无 identity 的旧条目 fail closed；
- `cleanup --dry-run`：按 event-level TTL 输出 exact delete / orphan-review / protected paths，
  不执行删除。

事件是 `agent.friction.event.v0` JSON，位于
`~/.ai/frictions/events/YYYY-MM/<event-id>.json`。cursor 位于
`~/.ai/frictions/cursors/<session-id>.json`，只优化增量状态；正确去重依赖 canonical
event ID。月度 rollup 位于 `~/.ai/frictions/rollups/YYYY-MM.jsonl`。

v0 产生 `task_aborted`、`patch_failure` 和 `repeated_file_edit_candidate`。`task_aborted` 只作为 deferred 事实保留，不单独触发 actionable；重复编辑候选至少需要 4 次成功 patch、跨 3 个 turn，减少正常两轮迭代噪声。普通 tool call
在现有 Codex JSONL 中只稳定暴露 completed，不能安全推出 process exit code，所以不生成
`tool_failure`。collector 不持久化 user / assistant message、tool input 或 tool output。

独立审计由用户显式请求触发，使用 `agent.audit.v1` semantic audit contract。helper 从 exact rollout 生成 bounded recovery packet，和可选 effective loop-ledger contract 一起放入隔离的本机 audit workspace；原始 rollout 不复制。通过 Rollerskate Codex Steward 选择已准入 Worker，异步投递后立即以 `run_id + receipt_path + output_path + summary_path` 记录 pending。显式 follow-up 收取并结算结果；engineering-exit 只交接 exact ledger path，不因 audit 缺席或 pending 阻塞用户可见终态，也不归档 ledger。结算方只按 receipt 绑定的 exact `ll_path` 延迟归档。报告分成 execution friction 与 prompt/final-form/loop-ledger fidelity gap 两条 lane，不建立第二套 event store；主 agent 逐条验证和结算，只有 promoted / deferred 内容进入 durable artifact。

## Ownership And Settlement

- owner 是 `unclaimed`、`context:<abbr>:<route>` 或
  `ll-contract:<exact-contract-path>`；禁止 latest-file 推断和全局 active pointer。
- 长会话可能包含多个任务，`checkpoint` 必须传 exact event IDs。`collect` 不自动把全部
  unclaimed events 归到当前任务。
- `/save-context` 负责 checkpoint 和 semantic settlement；context route identity 本身就是查询键，
  不扩展 `context.v2` 或复制 event body。选择 `promoted` 时必须同步形成 durable entry 或已确认 final-form。
- loop-ledger 写入并验证 exact session file 后才可 claim 同 route events。objective events 与单文件 loop-ledger 中仅用于当前任务 correction 的 feedback 是不同 schema 和 ownership；legacy future-loop feedback 与 `<session>.feedback.jsonl` 只作为迁移输入保留。
- `save-context` 在会话证据仍可用时结算当前 scope 的 objective events，但不成为 event owner。独立 audit 的结果由显式 follow-up 结算；promoted `global_friction` settlement 必须写入 normalized signature，helper 从可信 receipt 派生唯一的 `thread_id + project_cwd` occurrence，同一 settlement 内指向相同 `signature + durable_ref` 的多 lane item 共享该 identity，但只有主 Agent 的显式 `record-occurrence` 调用能修改 `agent-frictions.md`。`promoted` 必须同时形成该 durable entry 或用户确认的 follow-up final-form，`resolved` 必须关联已有 durable fix 或验证锚点。

## Relationships / Source Of Truth

- [Architecture index](./index.md)：架构 bundle 入口。
- [vertical-agent-ll](./vertical-agent-ll.md)：`save-context`、loop-ledger 与 `engineering-exit` 在完整 agent loop 中的职责。
- [Tool routes](../../tool-routes.md)：用户意图到 `agent-frictions` CLI 的稳定入口。
- [`scripts/agent_frictions.py`](../../scripts/agent_frictions.py)：事件 schema、采集、ownership、settlement 和 retention 行为事实源；[`scripts/test_agent_frictions.py`](../../scripts/test_agent_frictions.py) 提供独立回归 oracle。
- [`scripts/save_context_audit_rs.py`](../../scripts/save_context_audit_rs.py)：异步审计 workspace 的 dispatch、settlement/discard、归档打包、只读 inventory 与授权后回收事实源；[`scripts/test_save_context_audit_rs.py`](../../scripts/test_save_context_audit_rs.py) 提供独立回归 oracle。
- `skills/save-context`、`skills/load-context` 和 `skills/loop-ledger` 只拥有各自入口的调用与人机边界，不复制事件实现。
- `~/.ai/frictions/` 是本机运行态，不进入 Git，也不反向定义 durable 架构规则。
- `record-occurrence` 在 inbox 同目录的 `<inbox-name>.lock` 上持有旁路锁，覆盖完整读改写事务，避免并发登记丢失 occurrence；锁文件保留以稳定锁身份，原子替换只负责完整写入。既有记录含重复 identity 时拒绝写入。

## Retention

- `~/.ai/audits/save-context/<audit-id>/` 在异步结果结算、discard 或安全 supersede 前保留 packet、receipt、Run request 和结果；不保存原始 rollout。有效结果只有在 `settlement.json` 逐条覆盖全部 candidate 后才 `cleanup_ready`；terminal failed 且无有效输出时，status 先写 `inspection.json`，显式 `discard` 只消费匹配 run 的 terminal evidence；旧 dispatch contract 只有在同源 successor 已 `ready` / `settled` 后才能写 cleanup-ready `superseded` tombstone。系统不自动删除；prune 验证 workspace 严格位于当前 audit directory，默认只报告 exact paths。授权执行时先把固定白名单 evidence、manifest 和摘要原子写入 `~/.ai/audits/save-context/archived/YYYY-MM/<audit-id>.tar.zst` 并完整校验，成功后才移除 `workspace/` 与 `run.json`，保留 receipt、inspection 和 settlement tombstone；失败保留原现场且可幂等重试。历史 inventory 只读关联 Rollerskate archive 状态并报告 eligibility，不承担删除。
- Settled standard events 从 `settled_at` 起保留 30 天；显式 incident events 保留 90 天。
- Pending / claimed / deferred events 从 `last_owner_seen_at` 起判断；失去 active owner 30 天后
  进入 orphan review，不自动删除。
- Settlement 会把旧 owner 保存为 `settled_from` 并清空 owner，避免已结算引用永久阻止清理。
- Cleanup v0 只 dry-run。原始 Codex rollout 由 Codex 自己管理，不属于本工具清理范围。

## Decisions / Invariants

- Objective evidence 与语义解释分层；次数、abort 或 LLM annotation 都不能自动证明失败。
- 自动候选只负责召回：中断单独不可 actionable，成功重复编辑使用较高门槛且保持 deferred；semantic audit 必须证明“无效初始路线 → 可识别 fallback → 可避免额外成本”的完整序列。
- 执行 agent 不承担主动申报责任；独立 auditor 必须从 rollout 行为序列自行寻找未被当事 agent
  重视的 fallback 和 avoidable retry。
- Event 文件是唯一记录体；JSONL 用于交换与 rollup，不复制会话正文。
- workflow 入口调用同一 CLI，不各自解析 rollout 或维护第二套 schema。
- Context 保持恢复索引职责；event ownership 存在 event store，以 route identity 查询。
- 不自动 promotion、不自动修改 durable rules、不自动删除；`save-context` 负责为语义结算形成对应 durable 产物或明确补证条件。Occurrence identity 和计数是确定性写入：语义层选择 signature，脚本只验证可信 source、去重并计算 `复现 = distinct occurrence - 1`。

## Change Guidance

扩展 collector 时，先证明客户端提供独立结构化字段；不得为了新增指标开始解析 message 或
tool output 正文。新增客户端走 adapter，不改变 v0 event / owner / settlement 语义。新增自动
promotion 或删除能力必须另行设计授权、误报 oracle 和回滚方式。

修改事件 schema、ownership、lifecycle 或 retention 时，同时检查实现、回归测试、本 shard、tool route，以及受影响的 workflow skill；入口 skill 不应各自实现第二套 parser 或 store。最小验证入口为：

```bash
python3 -m unittest scripts/test_agent_frictions.py
python3 -m unittest scripts/test_save_context_audit_rs.py
scripts/agent-frictions --help
git diff --check
```

涉及真实 cleanup 时，先验证 `cleanup --dry-run` 的 exact path、owner protection 和 rollup 前置条件；dry-run 通过不构成删除授权。
