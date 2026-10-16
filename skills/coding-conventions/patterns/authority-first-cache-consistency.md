---
type: Pattern
title: 以权威存储为提交点的缓存一致性
description: 先识别权威事实与缓存分叉窗口，再按新鲜度、读写、持久性和修复能力匹配缓存模式及 pitfall。
resource: https://gitlab.example.com/example-org/iam/iam-vehicle-service/-/merge_requests/68
tags: [consistency, recovery]
---

# 以权威存储为提交点的缓存一致性

缓存设计先定位 authority 与 cache 的分叉窗口，再按 forces 匹配模式与 pitfall。若问题是 API 的 commit、visibility 或 session guarantee，使用 `operation-scoped-consistency-contract`；具体缓存策略评审只加载本 pattern。

## Context

- Authority 与 cache 不在同一原子边界，读写和删除可能并发。
- 系统正在选择缓存模式，并需要约束陈旧、RYW、撤权或删除复活风险。

缓存收益不足，或数据能安全留在一个事务存储时，先不加缓存。

## Problem

缓存模式名不能说明写到哪里算成功，也不能覆盖失效失败、旧 reader 回填、删除 key scope 丢失、绕行 writer 或 write-behind 提前确认等分叉窗口。忽略它们会把同步双写、长 TTL 或延迟双删误当成一致性证明。

## Forces

- **Authority**：谁决定事实与 commit point；cache 与网络可独立失败或 timeout。
- **Freshness and workload**：允许多旧、RYW 要求、读写比例、fan-out 与热点。
- **Writer coverage**：是否所有 writer 都经过同一入口或发布等价失效。
- **Repair capacity**：版本、retry、outbox / CDC、对账、告警与回源容量是否存在。

## Pattern

### 0. 先证明收益与机制必要性

从实际访问粒度、重复访问间隔、实例数量、依赖有效期及容量预算出发。先选择能满足正确性的最少机制，不把准入、短 TTL、多层缓存或观测组合成默认套餐。区分两种依据：一致性机制需要明确失效风险；收益和容量限制需要流量、成本或预算证据。

| 可选机制 | 采用前需要的证据 | 不足时的选择 |
| --- | --- | --- |
| 重复访问次数准入 | 一次性写入成本显著，且计数覆盖实际重复访问范围 | 不默认增加。共享缓存配 Pod 本地计数会漏掉跨 Pod 复用，不能用单实例访问推断整体热度 |
| 固定逻辑 TTL | 存在未被版本或事件覆盖的变化、时间型业务规则，或明确的最大陈旧期限 | 不用短 TTL 兜底代替失效协议。依赖版本与 epoch 已覆盖变化时，不再无依据强制周期重算 |
| 物理 TTL | 重复访问间隔、依赖有效期、写入量、条目大小和可用容量 | 不默认越短越安全。过短会阻断复用；超过依赖可用期也不保证继续命中。存在依赖校验时，物理保留不等于业务无条件有效 |
| 分段计时与逐请求观测 | 有明确排障问题、现有证据缺口、使用方及开销边界 | 日志精简只处理正文和级别，不顺手加入阶段探针、终态日志或新指标 |

评估收益时分别看源缓存和成品缓存，注明接口、主体、区域与流量窗口。成品命中低不能推出源缓存无收益，也不能直接比较不同流量区域。命中率不是唯一结论，还要核对避免的计算或回源成本，以及新增写入和存储成本。缺少证据时保留待验证项，不补一组保守默认值当作最优参数。

### 1. 先定位不一致窗口

对每类缓存对象写明 authority、commit point、cache role、key scope、允许陈旧度和 repair owner，再检查：

- Authority 已提交但 invalidate / set 丢失；或响应丢失后用新 identity 重试。
- 旧 reader 在 writer 提交并失效后重新填回旧值。
- Delete 后 key scope 丢失，旧列表、负缓存或派生输入复活对象。
- 绕行 writer 没有发布等价失效或版本推进。
- 成功响应早于持久化，使 cache / queue 实际成为 authority。

### 2. 按 forces 匹配缓存模式

- **Cache-aside**：数据库是 authority、读多写少时默认选择；miss 回源填充，write 提交后 invalidate。防止 stale refill、失效丢失、key scope 丢失和回源雪崩。
- **Read-through**：需要统一 loader、TTL、负缓存和 miss 合并时采用。Loader 不读落后副本、不缓存临时错误，旧结果不能覆盖新版本；它不定义写一致性。
- **Write-through**：所有 writer 收敛到同一 gateway，且当前读路径需要立即可见时采用。同步双写并非原子提交；严格 RYW 仍需版本读屏障或 authority fallback。
- **Write-behind**：只有前置层具备持久日志、复制、顺序、幂等、checkpoint、backpressure 和恢复时采用。此时 commit point 已前移，易失 cache 不得承载已确认写入。

### 3. 应用跨模式安全门

- Fill 与 writer 携带 version / generation；双删只缓解已证明的 stale refill，第二删必须持久、幂等且 delay 有依据。
- Delete 前固定 key scope；负缓存、列表和派生 key 共享 generation 或 tombstone。
- 提交后的缓存动作进入 durable retry / outbox / CDC，并记录 lag 与修复结果。
- Cache 不可用时，回源有容量预算、限流、热点保护和降级策略。

## Failure Modes

- 只写模式名，没有 authority、步骤顺序和失败响应。
- DB 提交后 cache 失败，却返回普通失败并诱发重复写。
- 无版本比较地 `set`，让慢 writer 或旧 loader 覆盖新事实。
- 把延迟双删或长 TTL 当成严格一致性证明。
- Delete 只清对象 key，遗漏列表、负缓存与派生 key。
- Write-through 存在绕行 writer，或 write-behind 使用易失 cache。
- Cache 故障时无保护地全量回源，放大为 authority 故障。

## Implementation Checklist

- 先绑定访问粒度、重复间隔和容量约束；每项额外机制说明它解决的独立缺口。
- 标出 authority、commit point、key scope 与 repair owner，再按 forces 选模式。
- Cache-aside 默认 authority commit 后 invalidate，并保存删除前 key scope。
- Read-through 定义 loader 来源、错误分类、miss 合并和旧回填防护。
- Write-through 收敛 writer；write-behind 具备 durable log、顺序、重放和 backpressure。
- 为 refill、delete、negative cache 和 retry 建立版本屏障。
- 定义 TTL、lag SLO、持久修复、告警和缓存故障回源容量。

## Verification

- 只验证选中机制的真实风险，不因本清单补齐未采用机制。
- 使用同类流量比较修改前后的命中、回源、写入和容量；多实例准入要验证跨实例重复访问。
- 重现 stale refill 顺序，验证旧填充被版本拒绝或最终失效。
- 在 authority commit 后终止进程或让 cache 失败，验证结果与修复契约。
- 打乱并发 writer、loader 与 retry 的完成顺序，验证旧版本不能覆盖新版本。
- Delete 后重放旧 fill、列表和负缓存，再 recreate，验证屏障与新版本语义。
- 暂停失效 consumer，验证 lag 告警、回放和 reconcile。
- 关闭 cache 并施加真实读流量，验证回源容量与降级边界。
- 对 write-behind 注入故障，验证已确认写不丢失且顺序不反转。

## Evidence

- [`iam-idaas-auth-service!472`](https://gitlab.example.com/example-org/idaas/iam-idaas-auth-service/-/merge_requests/472)：共享 Redis 成品配有 Pod 本地复用计数，另有固定逻辑期限。该变更移除两项限制，保留版本、epoch 与策略准入检查。该样本支撑按场景选择机制，不证明准入或逻辑 TTL 普遍无用。

- 真实命中：[`iam-vehicle-service!68`](https://gitlab.example.com/example-org/iam/iam-vehicle-service/-/merge_requests/68) 覆盖删除后失效与 key scope；[`iam-li-user-api@dcb508d`](https://gitlab.example.com/example-org/idaas/iam-li-user-api/-/blob/dcb508da8bc01301cb9f482321089a8a002edf1c/src/main/java/com/lixiang/iam/user/controller/ProfileMgmtController.java#L299-340) 覆盖 evict 与负缓存；[`iam-idaas-pip-service@d352e47`](https://gitlab.example.com/example-org/idaas/iam-idaas-pip-service/-/blob/d352e47b57eac5c15d9f25bdfdd93cbd187bee0c/src/main/java/com/lixiang/iam/pip/service/impl/ResourceServiceImpl.java#L185-237) 覆盖写后失效与回填。
- 独立复现次数：3 个服务仓库命中 authority commit 后的缓存修复边界。
- 可迁移性判断：适用于 authority 与 cache 不共享原子边界、且需要在多种缓存模式间选型的系统；单一事务存储或 operation-level consistency contract 不迁移到本 pattern。

## Relationships

- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
