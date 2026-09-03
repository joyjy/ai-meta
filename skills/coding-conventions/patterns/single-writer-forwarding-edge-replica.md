---
type: Pattern
title: 单写权威下的转发型边缘副本
description: 在共识 peer 网络暂不可用时，用单写 authority、星型投影、write forwarding 和版本化 write-through 保留多区域写入口与本地 RYW fast path，并明确向 quorum consensus 演进的可用性边界。
resource:
tags: [replication]
---

# 单写权威下的转发型边缘副本

多区域需要统一读写 API、但暂不能安全承载跨区域 consensus 时，由边缘副本把 mutation 转发给唯一 authority。提交后，入口用同一版本更新本地 projection，后台同步负责修复。

保留多区写入口，不允许分区独立提交。

## Context

- 每个区域连接本地数据库并需要低延迟本地读。
- 调用方不应认识 authority 的物理位置。
- 业务不能接受 split-brain 或事后冲突合并。
- 长期可能演进到 quorum consensus，但当前 peer 网络、身份、持久日志或运维能力不足。

托管共识存储或单一区域已满足需求时不使用本模式；分区两侧都必须提交时也不适用。

## Problem

普通异步复制只解决读副本收敛，不能定义谁提交 mutation，也不能保证写后本地可见。副本先写本地会形成多个 authority；没有版本化 write-through，本地读只能等待后台同步。

## Forces

- **Single authority**：同一事实只有一个排序和 commit point。
- **Local read**：正常读路径命中区域 projection。
- **RYW boundary**：write-through 是 fast path 还是严格 session guarantee 必须明确。
- **Concurrent apply**：snapshot、incremental、fallback 与 write-through 必须共享版本规则。
- **Evolution**：未来替换 authority 实现时保留命令、版本和 projection 契约。

## Pattern

```text
Client → Local Edge ─mutation→ Authority commit(version, after-image)
              │                         │
              └─read→ Local Projection ←┴─ snapshot / change stream
```

### 1. Authority 原子提交事实与变更

唯一 authority 在同一原子边界中更新事实、分配版本并写入 change / delete receipt；稳定 mutation identity 处理响应丢失。边缘副本只应用返回的权威结果。

### 2. Edge 只拥有 ingress

各区域暴露相同 API 并转发命令。使用 `forwarding replica` 或 `write ingress`，不把入口可达描述成 multi-primary。

### 3. 版本化 write-through 提供本地 fast path

入口以权威版本更新本地 projection，不生成版本、不推进后台 checkpoint，也不覆盖更高版本。

- **正常路径 RYW**：本地写穿成功时立即可见；失败后由后台修复。
- **严格 RYW**：响应携带 commit version，后续读用 `min_version` 等待追平或回源 authority。

本地写穿失败不能把已提交事实伪装成可回滚失败。

### 4. 后台同步拥有收敛与修复

固定 watermark 的 snapshot 负责 bootstrap，change stream 连续推进。所有 apply 路径共享版本比较、gap detection 与 delete barrier；write-through 不推进 checkpoint，旧输入不能覆盖新版本或复活删除事实。

### 5. 明确分区与演进边界

Authority 可达分区可以提交；断开的 edge 只能按契约读取本地 projection。演进到 consensus 时保留命令、mutation identity、结果和 projection 协议，只替换 authority 实现；fence 旧 writer，并保持版本连续或切换 epoch。Change stream 不能充当 consensus peer replication。

## Failure Modes

- 把多区域写入口描述成多区域独立提交。
- Edge 先写本地再通知 authority。
- Authority 提交事实与 change record 不在同一原子边界。
- Write-through 生成本地版本或推进后台 checkpoint。
- 多条 apply 路径各自实现覆盖与删除规则。
- Write-through 失败仍宣称严格 RYW，却没有读屏障。
- 把异步星型同步称为“简化 consensus”。
- Authority 切换或回滚时没有 fence 旧 writer。

## Implementation Checklist

- 固定 authority、commit point、mutation identity 和 unknown outcome。
- 原子提交事实、projection version 与 change / delete receipt。
- 所有本地 apply 路径复用版本比较、幂等与 delete barrier。
- 明确正常路径或严格 RYW；严格模式实现版本读屏障。
- Snapshot 固定 watermark，增量检测 gap 与 generation 变化。
- 写清 partition matrix、lag、repair、fallback 与 degraded read。
- Authority 演进包含 fencing、版本连续性、handoff 和 rollback gate。

## Verification

- 暂停后台同步后从 edge 写入，验证 authority 先提交且 checkpoint 不被 write-through 推进。
- 注入 authority 提交后本地 write-through 失败，验证业务结果保留且后台能修复。
- 让相同 mutation 在提交后响应丢失并重试，验证不会重复副作用。
- 并发执行 snapshot、incremental、fallback 与 write-through，验证旧版本和旧删除状态不能覆盖新状态。
- 隔离 edge 与 authority，验证本地不会私自提交。
- 演练 authority handoff，验证旧 writer 被 fence 且所有 projection 最终追平。

## Evidence

- [`iam-idaas-endpoint!16`](https://gitlab.example.com/example-org/idaas/iam-idaas-endpoint/-/merge_requests/16)：authority、forwarding 与 projection。
- [`iam-idaas-endpoint!17`](https://gitlab.example.com/example-org/idaas/iam-idaas-endpoint/-/merge_requests/17)：最小 projection scope。
- [`iam-idaas-endpoint!18`](https://gitlab.example.com/example-org/idaas/iam-idaas-endpoint/-/merge_requests/18)：write-through、RYW 与修复。

## Relationships

- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
