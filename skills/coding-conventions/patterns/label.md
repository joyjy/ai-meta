---
type: Reference
title: Pattern label
description: coding-conventions pattern 模块当前使用的 label 语义与回顾方式。
resource:
tags: []
---

# Pattern label

## Scope

本文件维护 `coding-conventions` pattern 模块当前实际使用的 label 语义和回顾方式。Label 用于跨 pattern 检索，不承担完整分类、正文摘要或实现细节索引。

Pattern concept 使用 OKF frontmatter 的 `tags` 保存 label，不额外定义 `labels` 字段。

## Current Labels

- `mq`：消息中间件的投递、消费、ACK 或 replay 边界是 pattern 成立的主要约束。
- `recovery`：pattern 主要解决失败执行恢复、retry、replay 或 backfill。
- `database`：数据库的索引、扫描、读写边界或事务语义是 pattern 成立的主要约束。
- `batch-processing`：pattern 主要处理数据分批推进、执行预算、checkpoint 或批次恢复。
- `distributed-lock`：pattern 主要处理跨进程互斥、租约、续期、owner 或 fencing 语义。
- `frontend`：浏览器 UI 的人类交互、客户端状态、异步请求或渲染提交边界是 pattern 成立的主要约束。
- `form`：按钮、输入框、选择器、表单提交或等价交互控件的输入与操作生命周期是 pattern 的主要触发面。
- `lifecycle`：组件启动、停止、排空、关闭顺序或生命周期边界是 pattern 成立的主要约束。
- `async-execution`：异步排队、运行中工作、准入和终止信号是 pattern 成立的主要约束。
- `data-modeling`：业务过程、粒度、事实、维度、指标口径或分析数据分层是 pattern 成立的主要约束。
- `replication`：单写或多写 authority、投影拓扑、版本收敛、read-your-writes、分区行为或共识演进是 pattern 成立的主要约束。
- `distributed-systems`：pattern 主要提供跨进程、节点、区域或存储协调状态时的通用决策框架，而不是绑定某一种中间件或算法。
- `consistency`：pattern 主要定义提交、读取可见性、会话保证、顺序、分区行为或陈旧度等一致性契约。

这些是当前已有 pattern 使用的工作语义，不是预先设计的封闭词表，也不构成固定分类轴。

## Usage

- 优先复用语义已经足够接近的 label。
- 正文、标题或 Pattern ID 已经能直接搜索到的实现词，不必逐个转成 label。
- 只有新 label 能改善跨 pattern 检索或区分明显不同的问题空间时才增加。
- 不预设每个 pattern 的 label 数量；数量应由实际检索价值决定。

## Review Guidance

新增或调整 pattern 时顺手回看 label。出现同义词分叉、含义重叠、长期只有单篇使用、标签无法帮助找到相关 pattern，或需要靠大量标签才能解释一篇文章时，及时合并、重命名或删除；不要为了维持既有分类而保留低价值 label。

Label 调整后，同步更新受影响 concept 的 `tags` 和 `coding-conventions` skill 内的 catalog，不在本文件保留迁移历史。

## Relationships

- [Consumer 自有的可重试执行单元](./consumer-owned-retryable-execution-unit.md)
- [UI Interaction](./ui-interaction.md)
- [基于主键扫描的破坏性清理](./primary-key-sweep-for-destructive-cleanup.md)
- [带 owner 校验与主动续期的分布式租约](./renewable-owner-checked-lease.md)
- [拥有异步资源的 graceful shutdown](./graceful-shutdown-anti-leak.md)
- [业务过程优先的数仓建模](./business-process-first-warehouse-modeling.md)
- [单写权威下的转发型边缘副本](./single-writer-forwarding-edge-replica.md)
- [故障模型优先的分布式状态设计](./failure-model-first-distributed-state-design.md)
- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [分离 Authority、Ordering、Replication 与 Projection](./authority-ordering-replication-separation.md)
- [coding-conventions](../SKILL.md)
