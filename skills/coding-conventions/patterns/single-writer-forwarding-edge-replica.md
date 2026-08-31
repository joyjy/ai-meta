---
type: Pattern
title: 单写权威下的转发型边缘副本
description: 在共识 peer 网络暂不可用时，用单写 authority、星型投影、write forwarding 和版本化 write-through 保留多区域写入口与本地 RYW fast path，并明确向 quorum consensus 演进的可用性边界。
resource:
tags: [replication]
---

# 单写权威下的转发型边缘副本

当系统希望每个区域节点都提供统一的读写 API，但当前基础设施无法安全承载跨区域共识通信时，让边缘副本接收写请求并转发给唯一 authority 提交；authority 返回带单调版本的提交结果后，入口副本立即把同一版本写穿到本地投影，后台再通过星型 snapshot / change stream 让所有副本最终收敛。

这个模式保留的是多节点写入口，不是多节点独立提交。只有 authority 拥有提交权；边缘副本的“可写”表示它能接收和转发 mutation，不能被解释为 multi-primary。

## Context

- 服务部署在多个区域或故障域，每个节点只连接自己的本地数据库，并需要低延迟本地读。
- 调用方希望所有区域暴露同一套读写 API，不永久绑定某个中心区域地址。
- 业务不能接受 split-brain、last-write-wins 或人工冲突合并，因此同一份事实必须保持单写。
- 长期目标可能是用 Raft 等 quorum consensus 在 leader 或区域故障后恢复写服务，但当前基础设施缺少跨集群 Pod 的稳定双向网络、peer identity、延迟保障或运维能力。
- 当前阶段仍需要先完成 authority 收敛、投影版本化、历史数据迁移和本地 read-your-writes fast path，不能把所有工作都推迟到共识基础设施具备之后。

如果基础设施已经提供成熟的托管共识存储，或业务可以直接把所有写请求路由到单一区域且不需要本地写入口，应优先使用更简单的现成能力。如果业务要求网络分区两侧都能独立提交，则需要 multi-primary、CRDT 或显式冲突解决；本模式和 Raft 都不提供这种语义。

## Problem

普通异步主从或星型复制只能让读副本最终收敛。它不能解释区域节点收到写请求时由谁提交，也不能保证刚完成的写立刻被本地读看到。直接让每个副本落本地库会形成多个 authority；只把写转发到中心节点则会让本地投影在后台同步追上前持续陈旧，并且容易把“所有节点都有写 API”误报成“分区期间所有节点都能写”。

系统需要在安全性、当前网络约束和未来共识演进之间建立一条明确边界：现在仍由单一 authority 排序和提交 mutation，同时保留多区域写入口、本地读、版本化投影和可替换的 authority contract。

## Forces

- **单写安全性**：同一业务事实只能由一个 commit point 排序，不能让网络故障自然退化成双写。
- **区域入口一致性**：调用方不应为了写操作认识当前 authority 的物理位置或切换细节。
- **本地读取延迟**：正常读路径应命中区域内投影，不为每次读取跨区访问 authority。
- **RYW 期望**：从某个区域入口完成写入后，紧随其后的本地读通常应看到该写；是否要求严格 session guarantee 必须单独声明。
- **最终修复**：入口 write-through 只能优化正常路径，后台同步仍必须修复进程退出、局部数据库失败和离线副本。
- **并发投影**：snapshot、incremental pull、fallback 和 write-through 可能同时修改同一条本地 route，必须共享版本比较和删除屏障。
- **结果不确定性**：authority 超时可能发生在提交前或提交后，重试不能把同一个业务意图变成冲突 mutation。
- **基础设施限制**：普通跨区 HTTP 服务可达不等于 Raft peer transport 可用；共识还需要稳定双向连接、成员身份、持久日志、时延预算和故障域设计。
- **演进连续性**：未来 authority 从单 DB 切换为共识状态机时，外部 API、命令语义和投影版本域不应被迫一起推倒重来。

## Pattern

```text
Client
  → Local Edge Replica
      ├─ read → Local Projection
      └─ mutation
           → Authority
               → authoritative commit + monotonic version
               → after-image / delete receipt
           → versioned local write-through

Authority
  → snapshot / change stream
      → Edge Replica A
      → Edge Replica B
      → Edge Replica N
```

### 1. 保持单一提交权威

所有 mutation 最终都由唯一 authority 提交。边缘副本可以鉴权、校验并接收写请求，但必须把业务命令转发给 authority；不能先写本地再异步争取中心接受。

authority 在一个原子提交边界内完成：

1. 分配与提交顺序一致的单调逻辑版本。
2. 更新或删除权威事实。
3. 写入可供投影消费的 change record；delete 必须留下带版本的 receipt 或 tombstone 事实。

authority 返回完整 after-image 或 delete receipt，而不是只返回“成功”。响应版本是后续 write-through、重试、对账和删除屏障的共同依据。

### 2. 用转发型副本保留多区域写入口

每个区域节点暴露相同的业务写 API，并把 authority location、token 和内部协议封装在服务实现内。调用方只认识本区域入口，不参与 leader discovery 或 authority 切换。

“副本可写”只能用于描述 API ingress，不用于描述数据 ownership。代码、文档和监控应使用 `forwarding replica`、`write ingress` 或等价词，避免把它误解为 multi-primary。

### 3. 用版本化 write-through 提供本地 RYW fast path

边缘副本收到 authority 的明确提交结果后，以同一个权威版本更新本地投影。write-through 不能生成新版本、不能推进后台 checkpoint，也不能覆盖版本更高的本地状态。

需要明确选择 RYW 契约：

- **正常路径 RYW**：authority 已提交且本地 write-through 成功时，立即本地可见；write-through 失败时仍返回权威提交结果，由后台同步修复。这是 fast path，不是严格 session guarantee。
- **严格 session RYW**：写响应携带 commit version，后续读携带或绑定 `min_version`；本地投影落后时等待追平或回源 authority。只有实现读屏障后，才能在局部投影失败时仍宣称严格 RYW。

不要为了维持本地投影而把已经提交成功的 authority mutation 伪装成业务失败；这会诱发调用方重试和结果不确定性。若业务必须把“本地立即可读”纳入写操作成功条件，应采用严格 RYW 模式并显式设计超时语义。

### 4. 用星型后台同步承担收敛和修复

authority 向所有边缘副本提供固定 high watermark 的分页 snapshot 和单调 change stream。每个副本维护独立 checkpoint、lease 和 source generation：

- snapshot 负责 bootstrap 或重建本地投影。
- incremental pull 从 snapshot watermark 之后继续消费。
- 重复 change 通过 per-record version 幂等处理。
- checkpoint 只代表后台流已连续消费到的位置，不能被单条 write-through 提前推进。
- 检测到 change gap、authority watermark 倒退或 stream generation 不可比较时必须停止，不能静默跳过。

星型同步是异步 projection / repair protocol，不参与 authority commit。它与 Raft log replication 即使拓扑相似，也不具有相同的正确性语义。

### 5. 统一所有本地写入路径的版本规则

write-through、snapshot、incremental pull 和 miss fallback 必须经过同一套本地 apply 规则：

- 只有更高或等价幂等版本可以生效，旧版本不能覆盖新版本。
- delete receipt 建立版本屏障；版本不高于屏障的 snapshot、fallback 或 change 不能复活记录。
- 更高版本的合法 recreate 可以清理旧屏障。
- authority miss 是明确的 absent 业务信号；其他网络或服务错误不能降级成 absent。
- fallback 返回早于本地 checkpoint 或删除屏障的结果时，最多服务当前请求，不应无条件回填本地库。

### 6. 只复制稳定的 control-plane 事实

星型投影只携带路由、ownership、状态、版本等完成本地决策所需的最小事实。高频变化或由其他 data region 拥有的 profile / domain payload 应在读取时向 owner 查询或由独立数据产品复制，不能顺手塞进 authority projection 形成第二事实源。

### 7. 把可用性边界写进契约

当前单 authority 模式在网络分区时的行为是：

- authority 所在可达分区可以继续提交。
- 与 authority 断开的边缘副本可以继续读本地投影，但不能独立提交新写。
- 所有节点都有写 API 不等于所有分区都有写可用性。

Raft 等 quorum consensus 的目标语义是多数派分区继续提交、少数派拒绝写，并在 leader 故障后由多数派选举恢复。它不会让网络分区两侧同时安全写入。两个 voting member 无法容忍任意一个失效；通常需要至少三个分布在明确故障域中的 voter，learner / read replica 不计入 quorum。

## Evolution to Quorum Consensus

把 authority 定义为稳定的命令与提交结果边界，而不是某张 DB 表或某个固定 Pod。当前实现可以由单数据库事务充当 authority；基础设施具备后，用 Raft state machine 替换其排序和提交实现：

```text
Current
  Edge mutation → DB Authority local commit → projection stream

Target
  Edge mutation → Raft Leader → quorum log commit → state machine apply
                                             → projection stream
```

可以保留的边界：

- 对外读写 API 和 forwarding replica ingress。
- mutation identity、幂等语义和 after-image / delete receipt。
- 单调逻辑 projection version，或显式可比较的 `authority_epoch + version`。
- snapshot / change projection、checkpoint、write-through 和本地版本屏障。

不能直接复用或混淆的部分：

- 当前异步 change pull 不能充当 Raft peer replication。
- DB sequence 不天然等于 Raft log index；业务 projection version 应显式定义。
- authority handoff 期间必须 fence 旧写入口、记录最终高水位并保证新 authority 的第一条 mutation 版本严格向前。
- 自动 Deployment rollback 不能替代已经接管写流量后的 authority 回切协议。

在选择 Raft 前先验证稳定 peer identity、跨故障域双向网络、延迟与丢包预算、持久卷、成员变更、snapshot、quorum 数量和故障演练。普通服务 HTTP 能跨区访问，只能证明 forwarding / projection 路径可用，不能证明共识基础设施可用。

## Failure Modes

- 把“每个节点接受写请求”写成“每个节点都可写”，导致调用方或运维误以为网络分区两侧能独立提交。
- replica 先写本地再异步通知 authority，遇到分区时形成事实分叉。
- authority 更新业务表后再异步生成 change record，崩溃窗口造成已提交事实永远无法投影。
- write-through 使用本地时间或新版本，破坏 authority 与投影共享的版本域。
- 单条 write-through 推进全局 checkpoint，导致后台消费者跳过尚未应用的较早 change。
- snapshot、incremental、fallback 和 write-through 各自实现覆盖规则，使旧响应覆盖新写。
- delete 只删除本地行而没有版本屏障，随后被旧 snapshot 或 fallback 复活。
- authority 超时后把同一业务意图当成全新 create 重试，实际已提交时产生冲突或重复副作用。
- write-through 失败仍宣称严格 RYW，却没有 `min_version`、等待或 authority fallback。
- 为了复制方便把 owner domain payload 一起投影，形成难以对账的第二事实源。
- 把异步星型同步称为“简化 Raft”，忽略 quorum commit、leader election、日志持久化和成员关系。
- 使用两个 voter 期待容忍一个节点故障，或声称 Raft 可以让多数派和少数派同时写。
- 在共识接管后直接启动旧 DB authority 回滚，造成两个 authority 同时分配版本。

## Implementation Checklist

- 明确 authority、唯一 commit point、mutation identity 和结果不确定时的重试语义。
- 在同一原子边界内提交业务事实、单调 projection version 和 change / delete record。
- authority 返回完整 after-image 或带版本 receipt；forwarding replica 不自行推导权威结果。
- 所有本地 apply 路径复用版本比较、幂等、checkpoint 锁和 delete barrier。
- 明确 RYW 是正常路径 fast path 还是严格 session guarantee；严格模式实现 `min_version` 读屏障。
- snapshot 使用固定 high watermark，incremental 从该水位继续，并检测 gap、generation 和 watermark 倒退。
- 将投影字段限制为完成本地决策所需的最小 control-plane 事实，标明其 owner。
- 明确 partition matrix：哪些分区可读、哪些分区可提交、写超时如何向调用方表达。
- 为 forwarding、fallback、sync lag、checkpoint、write-through failure、gap 和 tombstone 建立指标与告警。
- bootstrap 前冻结或隔离旧写入口，逐条处理 replica-only 数据、重复 key 和事实冲突。
- authority / replica 内部 API 使用最小权限认证，不能因网络在内部就跳过鉴权。
- 计划共识演进时，提前定义 fencing、版本连续性、handoff、回滚和至少三个 voter 的故障域布局。

## Verification

- 暂停后台同步，从非 authority 节点提交 create / update / delete，验证 authority 先提交且入口节点立即应用相同版本；后台 checkpoint 不被 write-through 推进。
- 让 authority 明确提交后注入本地 write-through 失败，验证业务结果不被伪装成 authority 失败、failure 指标出现，并在恢复后台同步后自动修复。
- 在 authority 提交后、响应返回前制造超时，再用相同 mutation identity 重试，验证返回当前权威结果而不是重复提交。
- 并发执行 snapshot、incremental、fallback 和 write-through，验证较低版本不能覆盖较高版本。
- delete 后重放旧 snapshot 和 fallback，验证版本屏障阻止复活；再用更高版本 recreate，验证旧屏障被安全清理。
- 丢失 checkpoint 后重新 snapshot，验证原地恢复不会清空更高版本本地状态，随后能从固定 watermark 连续追增量。
- 对每个区域入口和每类 ownership 数据执行交叉读写矩阵，验证本地入口能路由到正确 authority / owner，而不是只测试本区数据。
- 断开 edge replica 到 authority 的网络，验证本地读继续、写明确失败或超时，且系统没有本地私自提交。
- 在共识目标方案中分别终止 leader、隔离少数派和隔离多数派，验证只有 quorum 一侧可提交；两 voter 配置不得被验收为单故障可用。
- 执行一次 authority handoff 和计划内回切演练，验证旧 authority 被 fence、版本严格向前、所有投影最终收敛。

## Evidence

- [`iam-idaas-endpoint!16`](https://gitlab.example.com/example-org/idaas/iam-idaas-endpoint/-/merge_requests/16)：建立单 DB authority、转发型 replica、星型 snapshot / change stream、checkpoint 和版本化投影。
- [`iam-idaas-endpoint!17`](https://gitlab.example.com/example-org/idaas/iam-idaas-endpoint/-/merge_requests/17)：将 profile 留在所属 data region，只复制完成路由决策所需的事实。
- [`iam-idaas-endpoint!18`](https://gitlab.example.com/example-org/idaas/iam-idaas-endpoint/-/merge_requests/18)：补齐 versioned write-through、正常路径 RYW、delete barrier、失败修复和跨区验证。

## Relationships

- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
