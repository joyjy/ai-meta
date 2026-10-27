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

为当前变更涉及的操作说明调用方需要的保证，相同保证可以合并描述。只展开适用维度，不因本清单增加会话、分区或恢复能力。

### 1. Operation 与不变量

写明操作涉及的事实、owner、冲突范围和必须保护的不变量。同为 read 的权限检查、资料展示和审计查询也可能有不同契约。

### 2. Commit point 与响应

指出事实何时不可由正常失败路径撤销，以及成功响应是否包含 projection 可见或异步副作用。提交后响应丢失属于 unknown outcome，调用方通过稳定 mutation identity、状态查询或补偿处理。

### 3. Read visibility

声明读取来源和允许版本范围：linearizable；带可测上界的 bounded staleness；有明确收敛前提的 eventual；或无硬上界的 best-effort local。异步 projection 不因“通常很快”获得权威读取语义。

### 4. Session guarantees

业务需要会话保证时再选择。严格 RYW 通常需要 commit version、`min_version`、等待投影或回源 authority；write-through 和 sticky session 只能在其失败边界内提供 fast path。

### 5. Partition 与 latency

说明当前调用跨越的边界及失败响应。承诺分区可用性时，再展开对应断连关系。版本或降级信息由调用方契约决定；正常路径注明实际跨区、等待或回源成本。

### 6. Convergence 与 repair

先选择全量刷新、按需重建或增量维护。全量刷新或重建能满足契约时，复用现有读取和替换能力。采用增量、乱序输入或存在删除复活风险时，再选择版本、checkpoint、gap 检测和删除屏障。

承诺有界陈旧时明确可验证上界。承诺最终一致时说明收敛前提和修复责任；允许人工修复时可复用已有查询与补做入口。Best-effort 视图如实声明限制，不自动增加 lag SLO 或后台 reconcile。

## Failure Modes

- 用系统级“强一致 / 最终一致”替代逐操作保证。
- 把 CAP 当成静态三选二，忽略它约束分区期间的响应。
- 把 write-through、sticky session 或缓存命中率当成严格 RYW。
- 只说明写成功，不说明 projection、异步副作用或参与者状态。
- 把 timeout 当成明确失败并用新 identity 重试。
- 声称 bounded 或 eventual，却没有上界、收敛前提与 repair owner。

## Implementation Checklist

- 为当前操作或同类操作组明确事实 owner、不变量和 commit point。
- 分开定义成功、明确失败与 unknown outcome。
- 为 read 指定来源与可见性，只提供业务要求的会话保证。
- 存在分区可用性承诺时，说明对应断连关系下的行为。
- 同时声明正常路径的 latency / consistency 取舍。
- 按刷新方式和失败后果选择 projection 的版本、恢复和时限机制。

## Verification

验证当前承诺的主路径与最大真实风险，不因清单增加保证。

- 并发会影响可见性契约时，构造对应读写顺序并核对结果。
- 承诺 RYW 或 monotonic guarantees 时，再切换对应节点、区域或 session 验证。
- 承诺有界陈旧时，制造超过上界的 lag，验证等待、回源或降级。
- 写入存在响应丢失风险时，验证结果查询或既有重试契约，避免把未知结果当作确定失败。
- 全量刷新或重建时，验证更新与失败后的行为；增量维护时，验证适用的重复、缺口或删除处理。
- 承诺最终一致时，证明视图在声明条件下收敛。

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
