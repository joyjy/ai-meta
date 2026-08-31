---
type: Pattern
title: 分离 Authority、Ordering、Replication 与 Projection
description: 把接收命令、提交权威事实、决定事件顺序、复制已提交状态和构建查询视图拆成独立职责，再选择单写、共识、多主或可合并数据结构。
resource:
tags: [distributed-systems, replication]
---

# 分离 Authority、Ordering、Replication 与 Projection

分布式状态架构中，“哪个节点能写”“数据怎么同步”通常混合了多个不同问题。设计应分别说明谁接收命令、谁有权提交事实、谁决定冲突操作的顺序、哪些副本参与提交，以及哪些节点只保存派生查询视图。

## Context

- 多个区域或节点暴露相同 API，并各自保存部分或全部状态副本。
- 团队正在比较主从复制、星型同步、Raft / Paxos、multi-primary、CRDT、2PC / 3PC 或异步事件投影。
- 节点可能可接收写请求但不能独立提交，或者可本地提交但需要后续冲突合并。
- 读模型、缓存和控制面状态需要靠异步同步获得低延迟，但不应成为第二事实源。

## Problem

“主从但从可写”可能至少有三种完全不同的含义：从节点只接收并转发写请求，从节点先本地提交再复制，或多个节点都能提交但通过冲突规则收敛。如果只用“可写”和“同步”描述，调用方、实现者和运维会对分区行为与故障恢复形成不同预期。

同样，Raft 的 leader 向 followers 复制日志和 authority 向边缘节点推送 projection 都可能呈现星型流量，但前者的 follower 参与 quorum commit 与 leader election，后者通常只复制已经提交的事实。拓扑相似不代表协议语义相同。

## Forces

- **统一入口**：所有节点可能需要暴露同一 API，隐藏 authority 或 leader 的物理位置。
- **唯一事实源**：业务不变量可能要求一次只有一个提交序列，不能在分区中产生冲突事实。
- **分区写可用性**：某些业务确实要求多个隔离分区继续接受写，需要可合并状态或显式冲突裁决。
- **顺序需求**：有些操作只需要 per-key 顺序或因果顺序，有些要求单一全序；全局物理时间通常不是可靠答案。
- **提交参与者**：副本可能参与 quorum、atomic commit，或完全不参与提交而只异步追赶。
- **本地读取**：派生视图需要低延迟、可重建和版本化，但不能无意中接管 owner 职责。
- **演进成本**：从单 authority 迁移到 consensus 或 multi-primary 时，稳定的命令、版本和投影边界应尽量保留。

## Pattern

在架构图和接口契约中显式拆开以下职责。一个进程可以承担多个职责，但职责不能因为同址部署而合并成一个模糊的“节点角色”。

### 1. Ingress：谁接收命令

Ingress 负责对外 API、鉴权、校验、路由和结果返回。它可以在每个区域存在，并把命令转发到 authority 或当前 leader。

“每个节点都能接收写 API”只证明多入口可达，不证明每个节点都能在网络分区时独立提交。文档应使用 forwarding replica、write ingress 或 leader proxy 等准确名称。

### 2. Authority：谁能提交事实

Authority 定义唯一 commit point 和权威结果。它可以是单数据库事务、Raft quorum 已提交日志、特定数据 owner，或允许多 authority 的业务规则集合。

Authority 回答“什么事实算成立”，不是“哪台机器保存了一份数据”。副本数量和写 API 数量都不能替代 authority 定义。

### 3. Ordering：谁决定先后与冲突

先确定业务需要的顺序范围：per-key、per-session、causal、partition-local 或 global total order。只在不变量需要时支付更强顺序的协调成本。

Lamport 的 happens-before 关系表达因果偏序；逻辑时钟可在不依赖同步物理时钟的前提下构造与因果关系一致的顺序。若使用全序、term + log index、sequence 或 hybrid clock，必须说明它的比较域、epoch 和重启 / handoff 语义。

### 4. Commit replication：谁参与决议

把参与提交的复制与提交后的数据传播分开：

- Raft / Paxos 类 consensus replica 对命令顺序和已提交状态达成一致，quorum 是提交条件的一部分。
- 2PC / 3PC 类 atomic commit 协调多个事务参与者对同一事务提交或放弃，不负责建立一个长期复制状态机的 leader 与日志顺序。
- 同步数据库副本可能影响 durability 或 failover，但其 ACK 是否构成业务 commit 必须以数据库契约为准。

不要因为多个节点都收到相同数据，就默认它们参与了同一种 commit protocol。

### 5. Projection replication：谁保存派生视图

Projection 把已经提交的权威事实复制、转换或聚合到本地读取模型。它通常通过 snapshot、change stream、outbox、CDC 或消息消费异步推进，不参与原命令 commit。

Projection 必须带 source version、checkpoint、幂等 apply、gap detection、删除屏障和 reconcile path。它可以为正常路径提供本地 RYW fast path，但严格会话保证需要额外读屏障或 authority fallback。

### 6. Conflict model：多个 authority 如何收敛

如果网络分区两侧都必须独立提交，就不能只说“多主同步”。逐个数据类型定义：

- 操作是否可交换、可结合、幂等或具有自然单调性。
- 冲突能否由 CRDT / merge function 自动收敛。
- 是否允许 last-write-wins，以及时钟错误和丢失更新的业务后果。
- 无法自动合并时由谁仲裁，如何保留完整冲突证据。

不满足这些条件时，应保留单 authority 或 quorum authority，并接受非 quorum 分区停止写入。

### 7. 用角色组合比较候选架构

- **单 authority + forwarding edge + projection**：所有区域可接收写请求，只有一个 commit point；authority 不可达时边缘分区不能提交，但本地视图可继续读。
- **Raft state machine**：leader 接收或代理命令，多数派复制日志后提交；leader 失效时多数派可选举恢复，少数派拒绝写。
- **Multi-primary + conflict resolution**：多个 authority 可独立提交，分区写可用性更高，但顺序和不变量必须能通过合并、仲裁或业务约束恢复。
- **CRDT / monotonic state**：把状态限制为可证明合并的结构，以协调成本换取受约束的数据模型。

比较时保持外部命令和提交结果契约稳定，再替换 authority / ordering 实现。不要把某个数据库 sequence、Raft log index 或物理时间戳直接泄漏为永久业务版本，除非已经定义跨 epoch 的稳定比较语义。

## Failure Modes

- 把可以接收并转发写请求的 replica 称为 multi-primary，误报分区写可用性。
- 从节点先写本地再通知单 authority，网络分区时形成多个事实源。
- 把异步星型 projection 称为“简化 Raft”，忽略 quorum commit、term、election 和持久日志。
- 把 2PC、consensus 和 replication 当成同一类“多节点确认”，没有说明参与者是在决定事务、命令顺序还是复制视图。
- 用 wall-clock timestamp 为并发写排序，却没有时钟误差、tie-break、epoch 和丢失更新语义。
- 让 projection 生成自己的权威版本、覆盖较新事实或在 authority miss 时私自推断删除。
- 选择 multi-primary 以获得可用性，却把真正的冲突处理留给 last-write-wins 或人工查库。
- 迁移 authority 时没有 fence 旧 writer，或直接把旧 DB sequence 与新 consensus log index 混在同一版本域。

## Implementation Checklist

- 在图和文档中分别标出 ingress、authority、ordering、commit participant 和 projection。
- 为每类 mutation 指定唯一 commit point、返回的权威结果和 unknown outcome 处理。
- 写清顺序范围、版本比较域、epoch、重启和 handoff 语义。
- 列出哪些副本参与 commit，哪些只影响 durability，哪些只是异步查询视图。
- 对 projection 定义 source version、checkpoint、幂等、gap、delete barrier、snapshot 和 reconcile。
- 明确每种网络分区下哪些 ingress 可达、哪些 authority / quorum 能提交、哪些 projection 只能陈旧读。
- 如果允许多个 authority，逐个状态类型证明冲突可交换、可合并或有明确仲裁 owner。
- 把 2PC / 3PC、consensus、replication、RPC transport 和存储机制放在各自职责层比较。
- authority 演进时保留稳定 command contract，并设计 fencing、version continuity、bootstrap 和 rollback gate。
- 监控 authority identity、term / epoch、commit index、projection lag、gap、conflict 和 repair 状态。

## Verification

- 从每个 ingress 发起 mutation，验证提交都落到声明的 authority / quorum，而不是在入口私自形成事实。
- 隔离 forwarding edge 与 authority，验证 API 可达不被误判为写可提交，且本地读按契约继续或降级。
- 对 consensus 方案终止 leader、隔离少数派和隔离多数派，验证只有 quorum 一侧能推进 commit。
- 并发提交同 key 与跨 key 操作，核对实际顺序只达到声明的 per-key、causal 或 total-order 级别。
- 暂停 projection 后继续权威提交，再恢复并重放重复 / 乱序 change，验证最终收敛且旧版本不能覆盖新版本。
- delete 后重放旧 snapshot，验证 tombstone / version barrier 防止复活。
- 对 multi-primary 候选制造双方并发写，逐项验证 merge law、冲突证据和人工仲裁流程，而不只验证无冲突同步。
- 执行 authority handoff 和回切，验证旧 writer 被 fence、版本域连续或明确换 epoch、所有 projection 可重新追平。

## References

- [In Search of an Understandable Consensus Algorithm](https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro)：说明 Raft 通过 leader、复制日志、quorum commit 和成员变更实现复制状态机共识。
- [Time, Clocks, and the Ordering of Events in a Distributed System](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)：定义 happens-before 与逻辑时钟，说明分布式事件顺序不应直接等同于物理时间。

## Relationships

- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
