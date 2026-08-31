---
type: Pattern
title: 按操作定义一致性与分区契约
description: 不给整个系统贴“强一致”或“最终一致”标签，而是逐个操作定义提交点、读取可见性、会话保证、分区行为、延迟取舍与未知结果。
resource:
tags: [distributed-systems, consistency]
---

# 按操作定义一致性与分区契约

一致性不是一个覆盖整个系统的形容词。设计应针对每一种读写操作分别定义：什么时刻算提交，哪些读取必须看到哪些写，网络分区时继续、等待还是拒绝，正常路径为了延迟允许多旧，以及 timeout 后调用方能确定什么。

## Context

- 同一个系统同时存在权威写、异步投影、本地缓存、跨区读取、后台同步和故障回源。
- 不同操作的重要性不同，例如权限变更要求立即生效，展示型 profile 可以容忍短暂陈旧。
- 团队使用“强一致”“最终一致”“CP / AP”“支持 RYW”等概括词讨论方案，但这些词无法直接生成测试和调用方契约。
- 系统需要比较读屏障、quorum read、leader read、本地投影、sticky session 或客户端版本 token 等实现。

## Problem

把整个系统归为一种一致性等级，会隐藏真正的决策。例如 mutation 可以由单一 authority 线性提交，但区域内查询只读异步投影；某个 session 在正常 write-through 路径上能立即读到自己的写，局部落库失败后却没有严格保证；网络分区时读操作仍可返回旧值，而写操作必须拒绝。

这些行为同时存在时，“系统是强一致”或“系统是 AP”都不够准确。缺少操作级契约会让实现、监控、测试和产品预期各自补全不同含义。

## Forces

- **提交语义**：客户端收到成功前，事实是在单节点事务、leader、quorum 还是多个事务参与者处确定。
- **读取模型**：读取可能要求 linearizable、causal、bounded staleness、eventual consistency 或仅 best effort。
- **会话保证**：read-your-writes、monotonic reads、monotonic writes 和 writes-follow-reads 解决的是客户端会话内不同异常，不应互相替代。
- **分区行为**：CAP 约束发生网络分区时的选择；没有分区时仍需权衡 consistency 与 latency、吞吐和成本。
- **可见性范围**：同一 session、本区域、所有区域或所有派生视图的可见性成本不同。
- **未知结果**：写 timeout 不能自动归类为失败；读 timeout 也不能证明状态不存在。
- **恢复目标**：eventual consistency 需要收敛前提、lag 目标、repair owner 和不可收敛时的处理方式。

## Pattern

为每个外部可观察操作维护一份独立的一致性与分区契约。至少包含以下字段。

### 1. 操作与不变量

说明操作读取或修改的事实、owner 和必须保护的不变量。不要先从“读接口 / 写接口”粗分；权限撤销、路由定位、资料展示和审计查询即使都是 read，也可能需要不同契约。

### 2. Commit point 与成功响应

指出写在哪个状态跃迁后不可被正常失败路径撤销，以及成功响应证明了什么：只是 authority 已提交、quorum 已提交、所有参与事务已决议，还是本地查询投影也已可见。

明确提交成功但响应丢失时的 unknown outcome 语义。调用方需要稳定 mutation identity、查询最终状态或补偿流程，而不是假定重试安全。

### 3. Read visibility

定义一次读取允许返回的版本范围和观察顺序，例如：

- **Linearizable read**：读取表现得像发生在调用与返回之间的单一点，并与同一对象的提交顺序一致。
- **Bounded-stale read**：允许落后，但版本差、时间差或 lag 有明确上界。
- **Eventual read**：在没有新写且通信与修复最终恢复的前提下收敛；不承诺固定时刻前可见。
- **Best-effort local read**：优先低延迟本地结果，陈旧度没有硬保证；不得换名为 bounded staleness。

如果读取来自 projection，应说明它是否参与 commit。没有参与 commit 的异步视图不能仅凭“同步很快”获得权威读取语义。

### 4. Session guarantees

按调用链实际需要选择会话保证：

- **Read-your-writes**：会话后续读取不会遗漏该会话已经完成的写。
- **Monotonic reads**：会话不会先看到较新版本，随后又看到较旧版本。
- **Monotonic writes**：同一会话的写按发起顺序生效。
- **Writes-follow-reads**：基于某次读取发出的写，不会提交到看不到该读取依赖的历史上。

严格 RYW 通常需要把 commit version 绑定到 session 或请求，并在读取时使用 `min_version` 屏障、等待投影追平或回源 authority。写后立即 write-through 只能证明正常路径 fast path；一旦 write-through 失败、session 漂移或读到其他副本，就不能继续宣称严格 RYW。

### 5. Partition behavior

分别说明调用方、authority、读副本、依赖服务和数据 owner 之间发生分区时，操作会：

- 在能证明不变量的分区继续并返回成功。
- 返回明确不可用或可重试错误。
- 在有界时间内等待后返回 unknown outcome。
- 返回陈旧数据，同时暴露版本、年龄或降级状态。

CAP 讨论的是分区发生时，一致性与每个请求都获得非错误响应之间的约束，不是让系统永久选择一个 CP / AP 身份。PACELC 提醒设计者继续说明没有分区时，为降低延迟是否接受更弱的一致性。

### 6. Normal-path latency contract

说明正常网络下读取是否跨区、是否访问 leader / quorum、是否等待投影，以及 cache 和 sticky session 的正确性作用。把延迟优化与一致性保证分开：本地缓存可能让 RYW 更常成功，但只有版本约束、session routing 或回源屏障才能把概率行为变成契约。

### 7. Convergence and repair

对非权威视图定义 source version、应用幂等、checkpoint、gap detection、snapshot / replay、删除屏障、最大可接受 lag 和对账责任。最终一致的验收标准不是“等一会儿数据会来”，而是在写停止、网络恢复且修复任务运行时，所有目标副本能被证明收敛到同一权威版本。

## Failure Modes

- 用“系统是强一致 / 最终一致”替代每个操作的提交点、读取来源和分区行为。
- 把 CAP 解释成架构选型时静态三选二，忽略它约束的是网络分区期间的响应。
- 把本地 write-through、sticky session 或缓存命中率当成严格 RYW 的充分条件。
- 只说明写成功，却不说明成功是否包含投影可见、异步副作用或跨事务参与者完成。
- 读取旧值时没有版本、年龄或降级标记，调用方无法区分“事实不存在”和“副本尚未追上”。
- 把 timeout 当成写失败并生成新的业务命令重试，造成重复提交或冲突副作用。
- 声称 bounded staleness，却没有可测量的版本 / 时间上界和超限行为。
- 声称 eventual consistency，却没有收敛前提、repair path、告警和永不收敛时的 owner。

## Implementation Checklist

- 按业务操作列出事实 owner、不变量和唯一 commit point。
- 为成功、明确失败和 timeout / unknown outcome 分别定义客户端语义。
- 为每类 read 指定来源、允许版本范围和是否参与 authority commit。
- 逐项选择需要的 session guarantee，不用 RYW 代替其他三种保证。
- 严格 RYW 使用 commit version、`min_version` 或等价读屏障；否则标为正常路径 fast path。
- 为每种网络分区关系写明继续、等待、拒绝或返回陈旧数据的行为。
- 同时声明正常路径的 latency / consistency 取舍，不只给 CAP 标签。
- 为异步视图定义 lag SLO、checkpoint、gap、replay、delete barrier 和 reconcile owner。
- 在 API 响应或诊断信息中暴露必要的 commit version、served version、staleness 或 degraded 状态。
- 让文档中的每个保证对应至少一个可重复的 history 或故障测试。

## Verification

- 为同一对象生成并发读写 history，对要求 linearizable 的操作使用模型检查或 history checker 验证。
- 写入后切换区域、节点和 session，验证严格 RYW、正常路径 RYW 与无 RYW 的边界符合声明。
- 先读取新版本再切换到落后副本，验证 monotonic reads；连续发起相关写，验证 monotonic writes 和 writes-follow-reads。
- 暂停 projection、制造 lag 并超过上界，验证 bounded-stale 操作等待、回源或明确降级，而不是静默返回过旧数据。
- 在提交前、提交后和响应返回前注入断网，验证 unknown outcome、幂等重试和状态查询契约。
- 分别隔离客户端与副本、副本与 authority、authority 与 quorum / participant，核对每个操作的分区矩阵。
- 停止新写并恢复通信，验证所有 eventual view 在声明条件下收敛；破坏 checkpoint 后仍能通过 snapshot / replay 修复。

## References

- [Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services](https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/cap.pdf)：形式化说明网络分区下原子一致性与可用性的约束。
- [Consistency Tradeoffs in Modern Distributed Database System Design: CAP is Only Part of the Story](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf)：用 PACELC 补充无分区时 latency 与 consistency 的取舍。
- [Session Guarantees for Weakly Consistent Replicated Data](https://www.cs.utexas.edu/~dahlin/Classes/GradOS/papers/SessionGuaranteesPDIS.pdf)：定义 read-your-writes、monotonic reads、monotonic writes 和 writes-follow-reads 四种会话保证。

## Relationships

- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
