---
type: Pattern
title: 故障模型优先的分布式状态设计
description: 在选择 Raft、主从复制、分布式事务或补偿机制之前，先用状态不变量、预期故障、时间假设、分区行为和恢复验证约束方案空间。
resource:
tags: [distributed-systems]
---

# 故障模型优先的分布式状态设计

分布式系统设计的起点不是挑选 Raft、2PC、消息队列或某个数据库，而是说明哪些状态必须共同成立、系统预期承受哪些故障、故障期间允许哪些操作继续，以及恢复后如何证明不变量仍成立。协议和中间件只是满足这些约束的候选机制。

## Context

- 一项业务能力跨越多个进程、节点、区域、数据库或消息系统，局部成功不再等同于整体成功。
- 网络可能延迟、丢包、重复、乱序或分区；节点可能暂停、崩溃、重启或丢失易失状态。
- 系统需要在安全性、可用性、延迟、成本和恢复复杂度之间做明确取舍。
- 团队正在比较单写复制、quorum consensus、multi-primary、CRDT、2PC、Saga、异步投影或其他机制。

如果状态只存在于一个可靠事务边界内，应优先保留单机设计。不要为了未来可能扩容而预先引入分布式协调。

## Problem

直接从技术名词出发容易形成伪比较：Raft 和星型同步都有“主节点把写传播到其他节点”，2PC 和共识都需要多个参与者确认，心跳和超时都像是在判断故障，但它们解决的状态问题、假设和失败边界不同。

如果没有先声明故障模型，设计通常会把“暂时没有响应”误当成“没有执行”，把本地时钟误当成全局顺序，把单节点故障恢复误当成网络分区可用，并在上线后才发现协议依赖的网络、持久化或运维条件并不存在。

## Forces

- **安全性不变量**：即使系统不可用，也不能出现哪些状态，例如两个 authority 同时提交、余额为负或删除后被旧副本复活。
- **活性目标**：在什么前提下操作最终必须完成，允许等待多久，哪些故障会暂停进展。
- **故障范围**：预期处理 crash-stop、进程暂停、消息丢失 / 重复 / 乱序、网络分区、磁盘故障、时钟偏移还是 Byzantine failure。
- **相关性**：多个节点可能共享机架、集群、数据库、网络出口、控制面或发布批次，实例数量不等于独立故障域数量。
- **时间假设**：同步、异步或部分同步模型会改变故障检测和共识活性的边界；timeout 只是怀疑信号，不是远端未执行的证明。
- **状态所有权**：同一事实可以被复制和投影，但必须知道谁能提交、谁能派生、谁能修复。
- **恢复与演进**：bootstrap、catch-up、handoff、回滚、重放和 schema / protocol 升级都可能重新打开已经关闭的正确性问题。

## Pattern

先写一个可验证的故障模型与状态契约，再选择协议。至少按以下顺序收敛设计。

### 1. 列出状态边界和不变量

先描述事实，不描述组件：哪些状态由谁拥有，哪些状态只是副本或派生视图，哪些跨边界关系必须原子成立。把不变量写成故障期间也必须成立的断言，而不是正常流程的愿望。

区分 safety 与 liveness：safety 回答“绝不能发生什么”，liveness 回答“在什么假设下最终会发生什么”。系统可以为了保护 safety 暂停写入，但不能用暂时可用掩盖事实分叉。

### 2. 枚举操作和结果三态

逐项列出 create、update、delete、read、handoff、replay 等操作的提交点、可重试边界和外部可见结果。远程调用不能只有成功与失败两态；timeout 或连接中断表示结果未知，可能发生在提交前、提交后或响应返回途中。

对于会产生副作用的命令，必须决定使用稳定 mutation identity、状态查询、幂等应用、去重记录还是业务补偿处理未知结果。不要让传输层重试隐式决定业务语义。

### 3. 写明故障与分区矩阵

至少覆盖以下故障类别，并对每类说明读、写、后台推进和恢复行为：

- 单进程崩溃、暂停和重启。
- 单实例或单可用区失效。
- 节点间高延迟、单向不可达和双向网络分区。
- 消息丢失、重复、乱序和长时间滞留。
- 磁盘写失败、持久化数据丢失和 checkpoint 损坏。
- 时钟回拨、漂移和不同节点时间不可比较。
- 滚动发布、协议版本混跑和人工回滚。

每个“继续服务”的结论都要指出依赖的 quorum、authority、缓存或陈旧度边界；每个“拒绝服务”的结论都要说明如何恢复和如何向调用方表达。

### 4. 声明网络、时间与故障检测假设

心跳、lease 和 timeout 只能在声明的时间与延迟假设下提供故障怀疑。完全异步模型中无法仅凭等待时间区分节点崩溃与消息延迟；实际系统依赖部分同步、稳定 leader 时段、时钟误差上界或外部 failure detector 获得活性。

把这些假设写成可观测预算，例如 peer 间延迟与丢包、最大时钟偏差、持久化确认语义、成员身份稳定性和允许同时失效的故障域数量。基础设施不能满足时，不应靠应用代码假装协议前提成立。

### 5. 按契约选择机制

机制选择应能回指具体约束：

- 单一事务边界足够时，使用本地事务和明确 owner。
- 需要一组副本对同一命令顺序达成一致，并允许多数派在部分故障下继续提交时，评估 quorum consensus。
- 多个事务参与者必须对一次提交共同接受或共同放弃时，评估 atomic commit，同时接受它与 coordinator / participant 故障相关的阻塞和恢复成本。
- 分区两侧都必须接收独立写入时，必须定义冲突是否可交换、合并或由业务裁决；不能把单 leader consensus 当成双边写可用方案。
- 只需要把已提交事实送到本地查询视图时，使用版本化 replication / projection 和可重放修复，不把它误称为共识。

### 6. 把恢复、迁移和回滚纳入同一模型

恢复不是协议之外的运维附录。明确 snapshot watermark、增量连续性、重复应用、删除屏障、旧节点 fencing、authority handoff、数据对账和不可自动回滚的切换点。

任何能改变 owner、顺序域、quorum 成员或状态版本的发布，都应有独立演练。代码回滚只有在不会恢复旧 authority、旧 schema writer 或不兼容协议参与者时才安全。

### 7. 让故障注入成为设计证据

验证不只覆盖 happy path。用可重复的实验制造崩溃窗口、延迟、重复、乱序、分区、时钟偏移和磁盘故障，观察不变量、外部响应、恢复时间与最终收敛。无法注入或观测的故障假设，应明确标为未证明风险。

## Failure Modes

- 先选 Raft、Kafka、Redis 或某个云产品，再反推它能解决所有状态问题。
- 只写“高可用”或“容灾”，没有允许同时失效的节点数、故障域和恢复目标。
- 把 timeout、心跳丢失或 lease 过期当成远端已经停止、请求没有提交的事实。
- 按节点数量计算冗余，却忽略节点共享数据库、集群、网络出口或发布批次。
- 用物理时间戳决定跨节点因果顺序或 last-write-wins，却没有时钟误差边界和冲突语义。
- 只验证单节点重启，不验证网络分区、旧 authority fencing、重复消息和提交后响应丢失。
- 把 bootstrap、回滚和人工修复排除在正确性模型之外，导致恢复动作破坏正常路径已经保证的不变量。
- 用“最终一致”解释任何暂时错误，却没有收敛条件、时间目标、repair owner 和无法收敛时的告警。

## Implementation Checklist

- 列出权威事实、派生状态、owner 和所有跨边界不变量。
- 为每个写操作定义唯一 commit point、mutation identity 和 unknown outcome 处理方式。
- 区分 safety、liveness、durability、availability 和 latency 目标。
- 明确 crash、pause、partition、message anomaly、storage failure、clock skew 和 rollout fault 中哪些在支持范围内。
- 画出实际故障域和共享依赖，不用 Pod / instance 数量代替独立性。
- 声明网络、时间、持久化和 failure detector 假设，并确认基础设施能提供。
- 为每类故障写清读、写、后台推进、错误表达和恢复行为。
- 让协议选择回指某一项不变量或活性目标，删除没有约束依据的机制。
- 把 bootstrap、reconcile、handoff、migration、rollback 和 decommission 纳入设计。
- 建立能证明不变量、lag、quorum、authority、checkpoint、冲突和修复状态的观测。

## Verification

- 在提交前、持久化后和响应返回前分别终止进程，验证请求的重试和查询不会造成重复副作用。
- 注入长延迟、丢包、重复和乱序，验证系统不会把传输异常转化为事实分叉。
- 隔离不同故障域组合，核对每个分区的读写行为与声明的矩阵一致。
- 让旧 authority、过期 lease owner 或旧协议版本重新上线，验证 fencing 和兼容 gate 阻止其提交。
- 制造 checkpoint 丢失、snapshot 中断和消息重放，验证状态可重建且删除不会被旧数据复活。
- 注入时钟回拨和偏移，验证正确性不依赖未声明的全局物理时间顺序。
- 执行一次计划内 handoff、灾难恢复和回滚演练，记录恢复目标、不变量检查与人工介入点。

## References

- [Impossibility of Distributed Consensus with One Faulty Process](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf)：说明完全异步系统中，即使只允许一个进程停止，也不能保证确定性共识总能终止；实际活性依赖额外的时间或故障检测假设。
- [Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services](https://www.cs.princeton.edu/courses/archive/fall19/cos418/papers/cap.pdf)：给出 CAP 的形式化模型，约束网络分区期间一致性与可用性的同时满足。
- [Time, Clocks, and the Ordering of Events in a Distributed System](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)：区分物理时间与事件的 happens-before 偏序，并给出逻辑时钟和全序构造。

## Relationships

- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
