---
type: Pattern
title: 以权威存储为提交点的缓存一致性
description: Cache-aside、read-through、write-through、write-behind / write-back 与 refresh-ahead 的场景选型；先查权威提交和分叉窗口。
resource: https://gitlab.example.com/example-org/iam/example-device-service/-/merge_requests/68
tags: [consistency, recovery]
---

# 以权威存储为提交点的缓存一致性

缓存设计先定位 authority 与 cache 的分叉窗口，再按 forces 匹配模式与 pitfall。若问题是 API 的 commit、visibility 或 session guarantee，使用 `operation-scoped-consistency-contract`；具体缓存策略评审只加载本 pattern。

## Context

- Authority 与 cache 不在同一原子边界，读写和删除可能并发。
- 系统正在选择缓存模式，并需要约束陈旧、RYW、撤权或删除复活风险。

缓存收益不足，或数据能安全留在一个事务存储时，先不加缓存。允许陈旧且能回源重建时，先检查现有过期与失效策略是否已满足要求。撤权、删除或已确认写入的不可接受后果，按具体契约保护。

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

对当前缓存对象明确 authority、commit point、key scope 和允许陈旧度。只检查实际读写路径涉及的窗口：

- Authority 已提交但 invalidate / set 丢失；或响应丢失后用新 identity 重试。
- 旧 reader 在 writer 提交并失效后重新填回旧值。
- Delete 后 key scope 丢失，旧列表、负缓存或派生输入复活对象。
- 绕行 writer 没有发布等价失效或版本推进。
- 成功响应早于持久化，使 cache / queue 实际成为 authority。

### 2. 按 forces 匹配缓存模式

此表是缓存模式的选型入口。没有脱离当前约束的统一最佳模式。先说明权威存储、允许陈旧度、writer 覆盖和恢复能力，再选择最简单的可行模式。

| 模式与检索关键词 | 成立条件与用途 | 决定性边界 |
| --- | --- | --- |
| 不加缓存 / no cache | 缓存收益不足，或权威存储已满足延迟与容量要求 | 不为套用模式新增一致性和恢复成本 |
| Cache-aside / lazy loading / 旁路缓存 | 权威存储决定事实；未命中时回源，写入提交后按契约失效 | 按允许陈旧度处理旧回填、失效丢失和失效范围；模式名本身不证明一致性 |
| Read-through / 读穿透 | 缓存组件统一 loader 与读取流程 | 只定义读取归属；写入顺序和失效仍需独立契约 |
| Write-through / 写穿透 | 所有 writer 经过同一入口；入口同步写入权威存储与缓存 | 双写不是原子提交；明确提交点与部分成功，严格写后读需要版本屏障或权威读取 |
| Write-behind / write-back / 异步回写 | 允许后续写入权威存储；前置层已有持久日志、复制、顺序、幂等和恢复 | 提交点已前移；易失缓存与进程内队列不能承载已确认写入 |
| Refresh-ahead / proactive refresh / 提前刷新 | 热数据有可预测的复用，且过期时回源会影响延迟或容量 | 是读取模式的可选补充；刷新遵循已选的新鲜度、失效和容量约束 |

Cache-aside client 内部封装 loader 时，也具有 read-through 的读取形式。两者描述的边界不同，可以组合。不能据此推导写一致性。

当业务要求读取最新已提交数据时，loader 必须使用满足该要求的数据源。读取落后副本可能在失效后再次填入旧值。Loader 错误不能当作数据不存在缓存。

负缓存、进程内并发回源合并（single-flight）、分布式锁、过期时间随机偏移与多级缓存均为可选机制。只有真实风险或容量证据支持时才采用。进程内回源合并不提供跨实例保护。

### 3. 按契约选择保护与恢复措施

- 旧回填或乱序写会突破新鲜度要求时，选择版本比较、条件写入或权威读取。采用延迟双删时，说明第二删的可靠性与延迟依据。
- 删除或撤权要求覆盖派生缓存时，固定 key scope，并选择失效、版本屏障或权威校验。已有过期策略满足契约时直接复用。
- 提交后的缓存动作必须可靠完成时，复用已有的 durable retry / outbox / CDC。允许过期后重建时，沿用已认可的过期和回源路径。
- Cache 故障回源可能超过容量时，再选择限流、热点保护或降级。已有存储容量和流量控制足够时直接复用。

## Failure Modes

- 只写模式名，没有 authority、步骤顺序和失败响应。
- DB 提交后 cache 失败，却返回普通失败并诱发重复写。
- 需要防止旧值覆盖时，缺少版本比较或等效保护。
- 把延迟双删或长 TTL 当成严格一致性证明。
- 删除契约要求同步失效，却遗漏列表、负缓存或派生 key。
- Write-through 存在绕行 writer，或 write-behind 使用易失 cache。
- Cache 故障时无保护地全量回源，放大为 authority 故障。

## Implementation Checklist

- 先绑定访问粒度、重复间隔和容量约束；每项额外机制说明它解决的独立缺口。
- 标出 authority、commit point、key scope 与 repair owner，再按 forces 选模式。
- Cache-aside 按失效契约处理 authority commit 与 key scope。
- Read-through 明确 loader 来源与错误分类，按风险选择回源合并和旧回填防护。
- Write-through 收敛 writer；write-behind 具备 durable log、顺序、重放和 backpressure。
- 每项版本、投递、持久修复或容量保护措施对应一个实际缺口。
- 只承诺必要的新鲜度和恢复时限，并选择可验证的过期、回源或修复路径。

## Verification

- 只验证选中机制的真实风险，不因本清单补齐未采用机制。
- 使用同类流量比较修改前后的命中、回源、写入和容量；多实例准入要验证跨实例重复访问。
- 需要防止 stale refill 时，重现对应顺序并验证选中的保护措施。
- 在 authority commit 后终止进程或让 cache 失败，验证结果与修复契约。
- 契约要求防止乱序或删除复活时，验证对应 writer、loader 和删除路径。
- 采用可靠失效投递时，验证失败后的回放或修复；采用过期重建时，验证过期与回源路径。
- 回源容量是当前风险时，验证 cache 故障下的容量与降级边界。
- 对 write-behind 注入故障，验证已确认写不丢失且顺序不反转。

## Evidence

- [`idp-auth-service!472`](https://gitlab.example.com/example-org/idp/idp-auth-service/-/merge_requests/472)：共享 Redis 成品配有 Pod 本地复用计数，另有固定逻辑期限。该变更移除两项限制，保留版本、epoch 与策略准入检查。该样本支撑按场景选择机制，不证明准入或逻辑 TTL 普遍无用。

- 真实命中：[`example-device-service!68`](https://gitlab.example.com/example-org/iam/example-device-service/-/merge_requests/68) 覆盖删除后失效与 key scope；[`example-user-api@dcb508d`](https://gitlab.example.com/example-org/idp/example-user-api/-/blob/dcb508da8bc01301cb9f482321089a8a002edf1c/src/main/java/com/example/iam/user/controller/ProfileMgmtController.java#L299-340) 覆盖 evict 与负缓存；[`idp-pip-service@d352e47`](https://gitlab.example.com/example-org/idp/idp-pip-service/-/blob/d352e47b57eac5c15d9f25bdfdd93cbd187bee0c/src/main/java/com/example/iam/pip/service/impl/ResourceServiceImpl.java#L185-237) 覆盖写后失效与回填。
- 独立复现次数：3 个服务仓库命中 authority commit 后的缓存修复边界。
- 可迁移性判断：适用于 authority 与 cache 不共享原子边界、且需要在多种缓存模式间选型的系统；单一事务存储或 operation-level consistency contract 不迁移到本 pattern。

## Relationships

- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
