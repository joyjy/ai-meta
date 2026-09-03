---
type: Pattern
title: 分离 Authority、Ordering、Replication 与 Projection
description: 把接收命令、提交权威事实、决定事件顺序、复制已提交状态和构建查询视图拆成独立职责，再选择单写、共识、多主或可合并数据结构。
resource:
tags: [distributed-systems, replication]
---

# 分离 Authority、Ordering、Replication 与 Projection

“哪个节点能写”和“数据怎么同步”混合了多种职责。本 pattern 只用于澄清角色与提交语义；若主要问题是故障假设、一致性保证或已确定的单写边缘拓扑，使用对应的更窄 pattern，不在这里重复设计完整协议。

## Context

- 多个节点或区域暴露相同 API，并保存部分或全部状态副本。
- “可写副本”“主从”“多主”“同步”无法说明谁真正提交事实。
- 团队正在比较 forwarding、consensus、atomic commit、multi-primary 或异步 projection。
- 本地读模型需要低延迟，但不能无意中成为第二事实源。

## Problem

副本“可写”可能只是接收并转发，也可能本地提交后复制，或允许多个 authority 通过冲突规则收敛。拓扑和 API 外形相似，不代表提交、分区和恢复语义相同。

如果职责没有拆开，调用方会把入口可达误解为分区写可用，把异步 projection 误解为 quorum replication，并让派生视图生成自己的权威版本。

## Forces

- **Ingress**：哪些节点可以接收命令和隐藏 owner 位置。
- **Authority**：什么状态跃迁构成唯一业务事实。
- **Ordering**：冲突操作需要 per-key、causal、partition-local 还是 total order。
- **Commit participation**：哪些副本参与决议，哪些只提高 durability 或保存 projection。
- **Conflict model**：多个 authority 是否能合并，或必须由业务仲裁。

## Pattern

### 1. Ingress 只拥有接收与路由

Ingress 可以遍布各区域，负责鉴权、校验、路由和结果返回。它能接收 mutation，不证明它能独立提交；文档使用 `forwarding replica`、`write ingress` 或 `leader proxy` 表达该边界。

### 2. Authority 定义事实

为每类 mutation 指定唯一 commit point。Authority 可以是单数据库事务、consensus quorum、特定数据 owner，或允许多 authority 的业务规则；它不是“保存了一份数据的节点”。

### 3. Ordering 独立声明

只为不变量需要的范围付出协调成本。说明顺序域、epoch 与 handoff 语义，不用 wall-clock timestamp 假装全局因果顺序。

### 4. 分开 commit replication 与 projection

Consensus replica 参与命令排序和 commit；atomic commit participant 决定同一事务提交或放弃；projection 只应用已经提交的事实。Projection 需要 source version、checkpoint、幂等 apply、gap detection、delete barrier 与 reconcile，但不因此获得提交权。

### 5. 多 authority 必须拥有冲突模型

如果分区两侧都可提交，逐类状态证明操作可交换、可结合、幂等或可由 merge function 收敛；否则指定仲裁 owner。无法证明时保留单 authority 或 quorum authority，并接受非权威分区拒写。

典型组合只有语义成立后才能命名：单 authority + forwarding ingress + projection；consensus state machine；multi-primary + conflict resolution；或受约束的 CRDT / monotonic state。

## Failure Modes

- 把能接收并转发写请求的副本称为 multi-primary。
- 副本先写本地再通知单 authority，形成多个事实源。
- 把异步星型 projection 称为“简化 consensus”。
- 把 atomic commit、consensus 和 replication 统称为“多节点确认”。
- 用物理时间戳处理并发写，却没有顺序域、epoch 与冲突语义。
- 让 projection 生成权威版本、覆盖新事实或推断删除。

## Implementation Checklist

- 在图和文档中分别标出 ingress、authority、ordering、commit participant 与 projection。
- 为每类 mutation 指定唯一 commit point 和权威结果。
- 声明顺序范围、版本比较域、epoch 与 handoff 语义。
- 区分参与 commit、影响 durability 和只保存 projection 的副本。
- 多 authority 逐类证明 merge law 或指定仲裁 owner。
- authority 演进时保持稳定命令边界，并设计 fencing 与版本连续性。

## Verification

- 从每个 ingress 发起 mutation，证明它们落到声明的 authority 或 quorum。
- 隔离 ingress 与 authority，验证 API 可达不会被误判为可提交。
- 暂停 projection 后重放重复、乱序和删除事件，验证旧版本不能覆盖新版本。
- 对 multi-primary 候选制造并发写，验证 merge law 与仲裁证据。
- 执行 authority handoff，验证旧 writer 被 fence 且版本域连续或明确换 epoch。

## References

- [In Search of an Understandable Consensus Algorithm](https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro)
- [Time, Clocks, and the Ordering of Events](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)

## Relationships

- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
