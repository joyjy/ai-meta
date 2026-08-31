---
type: Pattern
title: Consumer 自有的可重试执行单元
description: 在公共消息基础设施无法按 consumer 独立补发时，通过私有持久化边界和独立执行单元实现受控 retry 与 replay。
resource:
tags: [mq, recovery]
---

# Consumer 自有的可重试执行单元

当公共消息基础设施不能按 consumer 独立补发，而某个 consumer 又需要独立失败恢复、人工重放或批量 backfill 时，由 consumer 建立自己的持久化交接边界，并让 retry / replay 作用于可独立记录执行结果的 execution unit，而不是重新投递公共 topic。

## Context

- 服务消费公共或共享 topic，同一消息还会分发给其他 consumer。
- Broker 不开放补发权限，或补发只能作用于整个 topic，无法只影响当前 consumer。
- 当前 consumer 需要独立恢复失败任务、人工重放或受控 backfill。
- Handler 会产生数据库、缓存、外部 API 或其他需要幂等保护的副作用。

如果 broker 已提供隔离 subscription，且其 replay、retention、权限和可观测性足以满足当前 consumer，应优先使用现有基础设施，不额外建设本模式。

## Problem

Broker 的 delivery / replay 粒度与业务执行恢复粒度不一致。直接补发公共 topic 会重复触发其他 consumer；只把 consumer 注册成 handler 并重复调用，又缺少可确认的持久化边界、执行状态和副作用保护，无法可靠 ACK，也无法解释某次执行为什么再次发生。

## Forces

- 公共 topic 只适合承担共享事件的首次交付，不能成为单 consumer 的私有重试控制面。
- ACK 必须对应一个明确的 durability boundary：业务已经完成，或消息已经可靠移交给当前 consumer 自己控制的持久化队列。
- Broker 常见的 at-least-once delivery 会让同一原始消息重复到达。
- Retry 需要独立控制 attempt、退避、终止、并发和人工重放。
- 业务副作用是否安全，不能只依赖消息接收层去重。

## Pattern

```text
公共 Topic
  → Ingress Consumer
  → 私有 Inbox / Work Queue
  → Handler Runner
  → Retryable Execution Unit
  → Result / Attempt Ledger
```

职责边界：

- `Ingress Consumer` 校验消息、生成或读取稳定的原始消息标识、完成接收去重，并把消息可靠写入私有 Inbox / Work Queue。
- 私有 Inbox / Work Queue 保存原始 envelope 和来源位置，是当前 consumer 独立 retry / replay 的控制面。
- `Handler Runner` 负责领取任务、控制并发、执行、退避、终止与人工重放。
- `Retryable Execution Unit` 是最小可重复业务动作，必须能独立记录成功或失败，并对重复调用提供业务幂等或等价的副作用保护。
- Result / Attempt Ledger 记录每次执行为何发生、使用哪个 handler 版本、结果是什么以及是否仍可重试。

本模式默认在消息可靠写入私有 Inbox / Work Queue 后 ACK 公共消息；后续业务失败由当前 consumer 自己重试。如果业务要求只有最终副作用成功才能 ACK，可以延后 ACK，但仍需 Inbox 去重和幂等处理，避免 broker 重投与本地 retry 形成两套不一致的执行链。

至少区分这些身份和状态：

- `source_message_id`，或稳定的 topic / partition / offset 组合：识别原始交付并建立接收唯一约束。
- `execution_id`：识别一次独立执行，不把人工重放伪装成新消息。
- `trigger`：区分 initial delivery、automatic retry、manual replay 和 backfill。
- `attempt`、`max_attempts`、`not_before`、`status`：表达重试控制和终止状态。
- `handler_version`：解释旧消息使用新代码重放时可能产生的语义变化。

## Failure Modes

- 为了恢复一个 consumer 而补发公共 topic，导致其他 consumer 被迫重复处理。
- Consumer 失败后重新向同一公共 topic 发布自己，形成不可见的自循环和放大的消息风暴。
- 把所有 consumer 注册成 handler，却没有 Inbox、execution identity、attempt ledger 或终止状态；框架虽然能再次调用，但系统无法证明是否安全。
- 在消息尚未可靠落入本地控制面前 ACK，进程退出时造成不可恢复丢失。
- 只做接收去重，不保护数据库写入、外部调用等业务副作用，重试时仍产生重复结果。
- 同时依赖 broker retry 和本地 runner retry，却没有统一 ownership，造成并发执行、重试次数失真或提前进入终止态。

## Implementation Checklist

- 明确 ACK 对应“业务完成”还是“可靠移交”，并对崩溃窗口做出书面说明。
- 为原始消息建立稳定唯一键；重复 delivery 不应创建多份首次执行任务。
- 明确 execution unit 的输入、成功、可重试失败、不可重试失败和终止状态。
- 为副作用设计业务幂等键、条件更新、唯一约束或可验证的补偿策略。
- 明确最大 attempt、退避策略、下一次执行时间、并发限制和人工重放权限。
- 保留原始 payload 时，定义 retention、脱敏、schema 兼容和 handler version 策略。
- 日志与指标能关联 `source_message_id`、`execution_id`、trigger 和 attempt。

## Verification

- 在 Inbox 持久化成功、ACK 之前终止进程；broker 重投后只能得到一份逻辑任务。
- 在 ACK 之后、首次 handler 执行之前终止进程；任务仍能由 Runner 恢复。
- 让 handler 连续失败，验证 attempt、退避、终止和告警符合配置。
- 对同一原始消息并发 delivery 或人工重放，验证业务副作用不会重复生效。
- 在 handler 升级后重放旧消息，验证版本差异可见，schema 不兼容时能安全停止。
- 验证单个 consumer 的 replay 不会触发公共 topic 上的其他 consumer。

## Related Patterns

- Idempotent Handler：待提取。
- Transactional Outbox：待提取。
- Non-overlapping Scheduled Execution：待提取，重点是定时任务自碰撞、owner lease、续期和仅 owner 可释放。

## Relationships

- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
