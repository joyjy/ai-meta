---
type: Pattern
title: 按操作定义一致性与分区契约
description: 不给整个系统贴“强一致”或“最终一致”标签，而是逐个操作定义提交点、读取可见性、会话保证、分区行为、延迟取舍与未知结果。
resource:
tags: [distributed-systems, consistency]
---

# 按操作定义一致性与分区契约

一致性不是覆盖整个系统的形容词。本 pattern 只负责把外部可观察保证写成逐操作契约；它不选择 authority 拓扑，也不重复完整故障模型。

## Context

- 同一系统同时有权威写、异步投影、本地缓存或跨区域读取。
- 不同操作对新鲜度、可用性与延迟的要求不同。
- 团队使用“强一致”“最终一致”“CP / AP”或“支持 RYW”等概括词。
- 保证需要转化为调用方契约、监控和可重复测试。

## Problem

一个 mutation 可以线性提交，而普通查询只读异步 projection；某个 session 正常路径能看到自己的写，局部失败后却没有严格保证。给整个系统贴单一标签会隐藏这些差异。

缺少操作级契约时，实现、产品、测试和告警会分别补全不同含义，timeout、旧读和投影延迟也无法被稳定表达。

## Forces

- **Commit**：成功响应证明 authority、quorum、事务参与者或 projection 已完成到哪一步。
- **Visibility**：读取需要 linearizable、bounded-stale、eventual 或 best-effort local 中的哪一种。
- **Session**：是否需要 RYW、monotonic reads、monotonic writes 或 writes-follow-reads。
- **Partition and latency**：分区时继续、等待、拒绝或返回陈旧值；正常路径是否跨区或回源。
- **Unknown outcome and repair**：timeout 后调用方知道什么，非权威视图如何收敛。

## Pattern

为每个外部可观察操作维护以下契约，不用系统级标签代替字段。

### 1. Operation 与不变量

写明操作涉及的事实、owner、冲突范围和必须保护的不变量。同为 read 的权限检查、资料展示和审计查询也可能有不同契约。

### 2. Commit point 与响应

指出事实何时不可由正常失败路径撤销，以及成功响应是否包含 projection 可见或异步副作用。提交后响应丢失属于 unknown outcome，调用方通过稳定 mutation identity、状态查询或补偿处理。

### 3. Read visibility

声明读取来源和允许版本范围：linearizable；带可测上界的 bounded staleness；有明确收敛前提的 eventual；或无硬上界的 best-effort local。异步 projection 不因“通常很快”获得权威读取语义。

### 4. Session guarantees

逐项选择需要的保证。严格 RYW 通常需要 commit version、`min_version`、等待投影或回源 authority；write-through 和 sticky session 只能在其失败边界内提供 fast path。

### 5. Partition 与 latency

对客户端、authority、quorum 和读副本之间的分区，分别声明继续、等待、拒绝或陈旧读，并暴露版本或降级状态。同时说明正常路径是否跨区、等待 projection 或访问 quorum。

### 6. Convergence 与 repair

为非权威视图定义 source version、checkpoint、gap、幂等 apply、delete barrier、lag SLO 和 reconcile owner。最终一致必须能说明停止写入且通信恢复后如何证明收敛。

## Failure Modes

- 用系统级“强一致 / 最终一致”替代逐操作保证。
- 把 CAP 当成静态三选二，忽略它约束分区期间的响应。
- 把 write-through、sticky session 或缓存命中率当成严格 RYW。
- 只说明写成功，不说明 projection、异步副作用或参与者状态。
- 把 timeout 当成明确失败并用新 identity 重试。
- 声称 bounded 或 eventual，却没有上界、收敛前提与 repair owner。

## Implementation Checklist

- 为每个操作填写事实 owner、不变量和 commit point。
- 分开定义成功、明确失败与 unknown outcome。
- 为 read 指定来源、版本范围和 session guarantee。
- 对每种分区关系声明继续、等待、拒绝或陈旧读。
- 同时声明正常路径的 latency / consistency 取舍。
- 为 projection 定义 lag、checkpoint、gap、delete barrier 与 reconcile。

## Verification

- 构造并发读写 history，验证承诺的可见性模型。
- 写入后切换节点、区域和 session，验证 RYW 与 monotonic guarantees。
- 制造 projection lag 并超过上界，验证等待、回源或明确降级。
- 在提交前后和响应前断网，验证 unknown outcome 与幂等重试。
- 停止新写并恢复通信，证明 eventual view 在声明条件下收敛。

## References

- [CAP](https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/cap.pdf)
- [PACELC](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)
- [Session Guarantees](https://www.cs.utexas.edu/~dahlin/Classes/GradOS/papers/SessionGuaranteesPDIS.pdf)

## Relationships

- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
