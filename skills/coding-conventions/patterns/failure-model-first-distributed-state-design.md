---
type: Pattern
title: 故障模型优先的分布式状态设计
description: 在选择 Raft、主从复制、分布式事务或补偿机制之前，先用状态不变量、预期故障、时间假设、分区行为和恢复验证约束方案空间。
resource:
tags: [distributed-systems]
---

# 故障模型优先的分布式状态设计

分布式状态设计先回答“必须守住什么、会坏在哪里、故障时允许什么”，再选择协议或中间件。本 pattern 是机制选型前的入口框架；角色含义、一致性措辞或明确的单写边缘拓扑已经成为主要问题时，直接使用对应的更窄 pattern，不叠加加载本文件。

## Context

- 一项能力跨越进程、节点、区域、数据库或消息系统，局部成功不再等于整体成功。
- 网络、节点、存储、时钟或发布过程可能独立或相关地失败。
- 团队正在比较 consensus、atomic commit、multi-primary、CRDT、Saga 或异步投影。
- 安全性、可用性、延迟、成本与恢复复杂度需要明确取舍。

如果状态能留在一个可靠事务边界内，优先保留单机设计。

## Problem

从 Raft、2PC、消息队列或数据库产品名出发，会把机制外形误当成问题定义。相似的复制拓扑可能拥有不同提交语义，timeout 也不能证明远端没有执行。

没有故障模型时，设计往往只证明正常路径，把网络分区、相关故障、旧 owner 恢复、版本混跑和回滚留到上线后处理。

## Forces

- **Safety 与 liveness**：哪些事实绝不能分叉，哪些操作在什么条件下最终必须完成。
- **故障范围**：支持 crash、pause、partition、消息异常、存储故障、时钟偏移和 rollout fault 中的哪些组合。
- **相关故障**：实例可能共享数据库、网络出口、控制面、机架或发布批次。
- **时间假设**：timeout 和 lease 依赖延迟、时钟与 failure detector 上界。
- **恢复与演进**：bootstrap、handoff、replay、migration、rollback 会重新打开正确性边界。

## Pattern

### 1. 声明状态边界与不变量

列出权威事实、派生状态及跨边界不变量，分开写 safety 和 liveness。不要用组件名代替事实 owner，也不要把副本数量当成独立故障域数量。

### 2. 写故障矩阵

按进程、节点、网络、消息、存储、时钟和发布故障，分别说明读、写、后台推进与恢复行为。每个“继续服务”结论都指出依赖的 authority、quorum 或陈旧度边界；每个“停止服务”结论都说明错误表达与恢复入口。

### 3. 声明协议假设

把网络延迟、时钟误差、持久化确认、成员身份与允许同时失效的故障域写成可观测预算。基础设施不能提供前提时，不靠应用代码假装协议仍然成立。

### 4. 让机制回指约束

- 单一事务边界足够时使用本地事务和明确 owner。
- 需要副本对命令顺序达成一致并由多数派推进时评估 quorum consensus。
- 多个事务参与者必须共同提交或放弃时评估 atomic commit，并接受其阻塞与恢复成本。
- 分区两侧都必须提交时，证明状态可合并或指定冲突裁决；异步 projection 只传播已提交事实。

### 5. 把恢复作为设计证据

为 snapshot、checkpoint、fencing、handoff、回滚与重放定义不变量，并用故障注入验证。无法注入或观测的假设明确标为未证明风险。

## Failure Modes

- 先选技术，再反推它能解决全部状态问题。
- 只写“高可用”或“最终一致”，没有故障域、收敛条件和恢复 owner。
- 把 timeout、心跳丢失或 lease 过期解释为远端已停止或请求未提交。
- 按实例数量计算冗余，忽略共享依赖和同批发布。
- 用物理时间戳决定跨节点顺序，却没有时钟与冲突契约。
- 只验证单节点重启，不验证分区、旧 owner、混跑版本与恢复动作。

## Implementation Checklist

- 列出权威事实、派生状态和跨边界不变量。
- 分开声明 safety、liveness、durability、availability 与 latency 目标。
- 固定支持的故障类型、组合和相关故障域。
- 记录网络、时间、持久化和 failure detector 假设。
- 让每个机制回指一项不变量或活性目标。
- 把 bootstrap、reconcile、handoff、migration 与 rollback 纳入模型。
- 建立能观察 authority、quorum、lag、checkpoint、冲突与修复的证据。

## Verification

- 在提交窗口、响应窗口和恢复窗口分别终止进程，核对不变量与外部结果。
- 注入延迟、丢包、重复、乱序和网络分区，验证系统行为符合故障矩阵。
- 让旧 owner、过期 lease 或旧版本恢复，验证 fencing 与兼容 gate。
- 破坏 checkpoint 或 snapshot 并重放消息，验证状态能够重建且不会复活已删除事实。
- 演练 handoff、灾难恢复和回滚，记录未证明假设与人工介入点。

## References

- [FLP](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf)
- [CAP](https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/cap.pdf)
- [Time, Clocks, and the Ordering of Events](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)

## Relationships

- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
