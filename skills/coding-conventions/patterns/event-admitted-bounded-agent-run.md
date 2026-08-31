---
type: Pattern
title: 事件准入的有界 Agent Run
description: 当稳定领域事件反复触发可由 skill 完成的有界工作时，用确定性结构准入、版本化 Run 请求、Rollerskate 执行和 source-owned reconcile 组成可恢复自动化。
resource:
tags: [async-execution, recovery]
---

# 事件准入的有界 Agent Run

当外部消息、MR revision、定时 occurrence 或其他稳定领域事件反复触发一段“人工识别目标、调用 agent skill、检查产物、回写结果”的工作时，不要把整段业务判断塞进监听脚本，也不要让关键词直接授权副作用。由事件 owner 保存完整 envelope 和稳定 identity，确定性 dispatcher 只完成结构准入并编译有界 Run 请求，Rollerskate 拥有 Agent Run、Session、workspace authority、恢复和 trace，业务 skill 解释语义并生成产物，最终由 source owner 做 freshness、readback 和 terminal transition。

## Context

- 系统已有稳定事件源，例如 Lark `message_id`、MR revision、Issue ID、schedule occurrence 或其他可重放 identity。
- 人工处理流程会选择一个已存在的 skill 或 versioned workflow，输入范围和产物边界可以明确。
- 相同流程已经重复出现，或其 schedule / subscription / event contract 明确说明会持续发生。
- 结果能够通过 artifact、Issue URL、revision、readback 或结构化 terminal result 独立验证。
- 模糊意图、权限不足、过期输入和业务判断可以安全回退到 `needs_human`。

一次性探索、没有稳定输入 identity、无法界定权限或终态只能靠主观判断的工作，不适用本模式；优先保留 turn-based 协作或只产生 attention。

## Problem

直接在 watcher 或 dispatcher 里按关键词执行脚本，会把召回、业务授权、执行和 source transition 混成一个不可审计入口。重复消息、旧 revision、进程重启或模糊表达都可能产生重复副作用或错误执行，失败后也无法判断应该重试、等待人还是回到 source 重建。

另一种常见失衡是让通用 Agent Runtime 拥有业务状态。Runtime 虽能启动和恢复 Agent，却不应判断某条消息是否真的要求发布、某个 MR 是否仍是 desired revision，或某个 Issue 应进入哪个 lifecycle。把这些状态复制进 Runtime 会形成第二套事实源。

## Forces

- **唤醒不等于授权**：mention、URL、关键词或 event type 可以提高召回率，但不能证明完整业务意图或授权写操作。
- **语义判断需要 Agent**：自然语言意图、文档归纳和 skill 产物通常无法用固定规则完整表达。
- **执行必须有界**：workspace、network、effect、skill、输入、budget 和 terminal contract 不能由 Agent 自行扩大。
- **事件可能重复或过期**：at-least-once delivery、人工重试和旧 revision terminal result 都要求 dedupe 与 freshness gate。
- **业务事实有既有 owner**：消息、MR、Issue、WorkItem 和发布状态必须回到各自 source transition，不由 dispatcher 或 Rollerskate 复制。
- **失败需要恢复与介入**：provider failure、malformed result、权限不足和 source drift 需要可查询 trace、受控 retry 或 `needs_human`。

## Pattern

```text
stable domain event
  → source-owned envelope / dedupe identity
  → deterministic structural admission
  → versioned bounded Run request
  → Rollerskate Agent Run / Session / trace
  → skill-owned semantic decision and artifact
  → source-owned freshness / readback / terminal transition
  → optional attention or reply
```

### 1. Source owner 保存完整事实

事件 owner 保存完整、bounded envelope 和稳定 identity。监听只负责接收、去重和唤醒，不把 message text、MR state 或 Issue lifecycle 复制成新的长期事实源。外部推送或通知只携带回到可信 source 所需的最小 reference。

### 2. Dispatcher 只做结构准入

用 allowlist、actor/chat binding、mention、URL shape、schema、workspace mapping 和 risk policy 做确定性 preflight。准入成功只表示输入形状允许进入语义判断，不表示业务意图成立，也不自动授权写操作。关键词只能用于低成本召回；完整意图由 skill 基于完整 envelope 判断。

### 3. 编译版本化、有界 Run 请求

Run request 固定：

- source identity、dedupe / request ID 和 causation；
- exact skill 或 workflow revision；
- bounded input envelope 与目标；
- canonical workspace 和 `read | write` grant；
- network / effect authority、budget 和 deadline；
- structured result contract、artifact boundary 和 terminal condition；
- `needs_human` 与不可重试失败的返回语义。

重试相同 source revision 必须命中同一逻辑执行或被 source-owned dedupe 拒绝，不能靠 prompt 约定“请勿重复”。

### 4. Rollerskate 只拥有执行面

Rollerskate 拥有 Agent Run、Session、workspace authority、step、retry/recovery、cancel 和 trace。它不读取或推进消息、Issue、MR、WorkItem 或发布 lifecycle，也不从 artifact 内容推断业务完成。

### 5. Skill 拥有语义与产物

Skill 基于完整 envelope 解释业务意图，按自己的 source-of-truth、写入门禁和验证规则生成 bounded artifact 或结构化结果。语义不成立时返回“未执行及原因”，而不是让 dispatcher 用更多关键词补齐业务判断。

### 6. Source owner reconcile

Run terminal 后，source owner 校验 execution identity、input revision、当前 freshness、artifact/readback 和 effect receipt，再决定业务 transition、回复或 attention。旧 result、无法证明的写入和 delivery failure 不得伪装成 source success；delivery 可以从 source state 独立重试。

## Agent Recognition

Agent 在设计 final-form 或收束实现 diff 时，只有看到下面信号才评估本模式：

- 稳定事件反复进入同一人工或脚本处理链；
- listener / poller / dispatcher 后面存在明确 skill、agent invocation 或人工复制命令；
- 输出落为可验证 artifact、Issue、review package、readback 或 terminal receipt；
- source、dispatcher、Runtime、skill 和 artifact 的 owner 可以分别指出。

评估结果使用稀疏 `automation_candidate`，而不是修改当前任务的 dispatch target：

```yaml
automation_candidate:
  runtime: rollerskate
  fit: fit # fit | partial
  evidence: [<source or implementation anchor>]
  # missing_gates: [<exact unproven gate>] # required for partial
  smallest_experiment: <bounded one-shot verification>
```

- `fit`：稳定 identity、结构准入、有界 authority、dedupe/freshness、terminal oracle 和 human fallback 都已证明，可建议 one-shot 最小实验。
- `partial`：识别到重复链路，但至少一个硬门槛未证明；只列缺口，不建议自动启动 Run。
- 完全不匹配时省略字段，不输出空候选。
- 候选只是一条建议，不授权创建 GTD 任务、修改 automation、启动 Run 或写业务 source。用户确认后再由 GTD 承接改造任务。

## Failure Modes

- 命中关键词后直接执行写操作，把召回当成业务意图和授权。
- Dispatcher 重新实现 skill 的语义、source transition 或 completion 判断。
- 只传消息正文，不保留 message ID、actor、conversation、reply/root/thread 和来源 revision。
- 用“最新消息”“当前 MR”或“最近一次 Run”替代显式 source identity 与 revision binding。
- 让 Agent 自己选择 workspace、扩大 network/effect 或调用未登记的任意 shell。
- 用 prompt 要求幂等，却没有 request ID、唯一约束、readback 或 source freshness gate。
- Run terminal 就直接写 source success，没有核对当前 revision 和 artifact receipt。
- 把 Rollerskate 变成消息、Issue、WorkItem 或发布状态的第二 owner。
- 为一次性或软 oracle 工作建设自动 loop，反而隐藏人工判断和 acceptance 缺口。
- 自动创建 GTD 任务或继续改造，仅因为 agent 识别到候选。

## Implementation Checklist

- 指出 source event owner、稳定 identity、完整 envelope 和 retention / redaction 边界。
- 定义 dispatcher 的结构准入与明确非职责；关键词、mention 和 URL 不承担业务授权。
- 固定 skill/workflow revision、input schema、workspace grant、network/effect、budget 和 result contract。
- 定义 dedupe key、retry identity、freshness gate、并发冲突和取消语义。
- 定义 artifact/readback oracle，以及 source owner 如何 reconcile terminal result。
- 覆盖语义不成立、权限不足、stale input、provider failure、malformed result 和 delivery failure。
- 让日志和 trace 能关联 source identity、request ID、Run ID、artifact 和 source transition receipt。
- 在真正自动执行前先运行 one-shot 最小实验；未证明 gate 保持 `partial` 或 attention-only。

## Verification

- 重复投递同一事件，验证只产生一个逻辑执行和一次业务副作用。
- 发送结构合法但业务意图不成立的输入，验证 skill 返回未执行，dispatcher 不补做业务判断。
- 在 Run 开始后改变 source revision，验证 terminal reconcile 拒绝旧结果或转为 `needs_human`。
- 在 provider、进程和 delivery 各阶段制造失败，验证 retry、trace 和 source state 相互独立且可恢复。
- 尝试扩大 workspace、network、effect 或未登记 skill，验证 admission fail closed。
- 验证 artifact/readback 缺失时不会推进 source terminal state。
- 验证 `partial` 候选只报告缺口，不启动 Run、不创建 GTD 任务和不修改 automation。

## Evidence

- 真实命中：arch-hub Automated Lark Candidate Intake 使用完整消息 envelope、结构准入、独立幂等 intake、bounded Candidate write 和 terminal reply；证据入口为 `/Users/example/Documents/reference/arch-hub/release/skills/candidate/references/automated-lark-intake.md`。
- 真实命中：GTD revision-bound MR review 以稳定 WorkItem / revision 启动 Rollerskate `review@1` Run，终态再做 workspace revision freshness、review package 和 Human Review reconcile；证据入口为 `/Users/example/Documents/me/Projects/gtd/docs/architecture/workitem-projection.md` 与 `/Users/example/Documents/me/Projects/rollerskate/docs/architecture/local-review.md`。
- 独立复现次数：2 个不同 source domain 和 artifact contract 命中相同结构。
- 可迁移性判断：该模式适用于拥有稳定事件 identity、有界 skill 和 source-owned terminal oracle 的其他消息、MR、Issue、schedule 或 subscription 工作；缺少这些 forces 时不迁移。

## Relationships

- [Consumer 自有的可重试执行单元](./consumer-owned-retryable-execution-unit.md)
- [带 owner 校验与主动续期的分布式租约](./renewable-owner-checked-lease.md)
- [coding-conventions](../SKILL.md)
