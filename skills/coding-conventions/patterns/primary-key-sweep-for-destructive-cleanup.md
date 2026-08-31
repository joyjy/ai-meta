---
type: Pattern
title: 基于主键扫描的破坏性清理
description: 当清理条件缺少可用索引时，按稳定主键有界扫描、筛选候选，并通过带条件复验的精确 ID 删除安全推进。
resource: https://gitlab.example.com/example-org/amp/example-amp-service/-/merge_requests/100
tags: [database, batch-processing]
---

# 基于主键扫描的破坏性清理

当待清理数据的业务筛选条件没有可用索引，而系统又不适合立即增加联合索引时，可以把“发现候选”和“执行删除”拆开：使用已有的稳定主键完成可预测的 keyset scan，在应用层筛选候选，再按当前页的精确 ID 执行带业务条件复验的删除。

这个 pattern 利用了删除任务的特殊优势：成功处理的候选会从工作集中消失，checkpoint 丢失后的重复扫描通常只会得到无结果删除，而不会再次产生同一个业务副作用。它不是普通批处理的无条件替代方案。

## Context

- 清理条件主要落在时间、状态或其他非主键字段上，现有索引不能同时支持筛选、排序和小批量推进。
- 生产约束暂时不允许新增合适的联合索引，或索引成本高于当前清理收益。
- 表具有稳定、可排序且适合 keyset pagination 的主键。
- 任务允许渐进完成，可以用多次调度覆盖完整数据空间。
- 删除候选能够按精确 ID 执行，并在删除时重新检查业务条件。

如果业务查询已有合适索引，优先直接使用该索引筛选候选；不要为了套用本 pattern 主动放弃高选择性的索引。

## Problem

直接按业务条件查询通常会形成类似以下形状：

```sql
WHERE expire_time < :cutoff
ORDER BY expire_time, id
LIMIT :batch_size
```

当不存在 `(expire_time, id)` 一类匹配索引时，数据库可能扫描大量记录并执行 filesort。PRIMARY 只能提供按 `id` 的顺序，无法同时承担原查询的时间筛选和排序。

如果直接改成全表主键扫描，又会引入扫描放大、无限追逐新数据、checkpoint 失败后重复处理和并发删除竞态。

## Forces

- 扫描路径必须使用真实可用的索引，而不是依赖优化器偶然选择。
- 每页、每次任务和一次完整 sweep 都需要明确边界，避免长事务或无上限运行。
- 扫描完成不等于候选仍然满足删除条件；扫描与删除之间可能发生并发变化。
- Checkpoint 只有在当前批次的破坏性操作成功后才能推进。
- 删除后的安全重扫是一种优势，但扫描大量非候选记录仍然有成本。

## Pattern

```text
按主键 keyset 有界扫描
  → 应用层筛选当前页候选
  → 按精确 ID + 业务条件复验删除
  → 删除成功后推进 checkpoint
  → 到达执行预算、high-water mark 或业务边界后停止
```

扫描查询只承担稳定推进：

```sql
SELECT id, business_fields
FROM target_table
WHERE id > :cursor
ORDER BY id ASC
LIMIT :page_size;
```

只有 `EXPLAIN` 证明优化器没有选择预期主键路径，并且强制索引在目标数据分布上确实更稳定时，才使用 `FORCE INDEX (PRIMARY)`；不要把强制索引当成 pattern 的固定组成。

删除查询只接收当前页筛出的精确 ID，并重新检查安全条件：

```sql
DELETE FROM target_table
WHERE id IN (:candidate_ids)
  AND business_state = :expected_state
  AND expire_time < :cutoff;
```

边界至少覆盖三个层次：

- Page bound：限制单次查询和单次删除的 ID 数量。
- Execution bound：限制一次任务最多扫描的记录数、页数或运行时间。
- Sweep bound：使用固定 high-water mark、扫描到空页，或由明确业务不变量证明的终止边界；不能无条件追逐不断增长的新 ID。

Checkpoint 表示“最后一个已经完成当前页处理的扫描位置”。删除失败时不推进；删除成功但 checkpoint 写失败时允许从旧 cursor 安全重扫相关区间。只有删除具备精确 ID 和条件复验语义时，这种 at-least-once 推进才是安全的。

## Why Deletion Helps

- 已删除候选不会在后续 sweep 中继续占用业务处理预算，工作集会收缩。
- 重复删除同一 ID 通常是无结果操作；配合业务条件复验，可以把 checkpoint 失败转化为安全重扫。
- 精确 ID 删除可以使用主键点查，不需要让业务筛选条件承担删除阶段的索引职责。
- 删除前再次检查状态和时间边界，可以拒绝扫描后已经变化的记录。

这些优势不自动适用于批量更新、导出、通知或外部 API 调用。记录仍然存在或副作用发生在数据库外时，需要额外的幂等键、processed/version 标记、执行账本、outbox 或补偿机制。

## Failure Modes

- 原业务条件没有索引，却仍按该字段排序分页，导致大范围扫描和 filesort。
- 只限制 page size，不限制单次任务或完整 sweep，任务持续追逐新数据。
- 在删除成功前推进 checkpoint，失败时永久跳过尚未处理的记录。
- 先扫描 ID，删除时不复验业务条件，误删扫描后已经恢复或被修改的数据。
- 把主键与业务时间的相关性当作天然事实，未经验证就用时间边界提前结束 sweep。
- 候选密度很低仍频繁全表 sweep，把数据库读放大成本隐藏在“小批量”名义下。
- 把删除场景的安全重扫直接复制到外部副作用任务，产生重复通知、重复写入或重复扣减。

## Implementation Checklist

- 用生产代表性数据执行 `EXPLAIN`，确认扫描路径、排序方式、预估扫描行数和回表成本。
- 明确 cursor、page bound、execution bound 和 sweep bound 分别由什么保证。
- 如果用 `id` 与 `create_time` 单调关系提前结束，记录并验证这个业务不变量。
- 删除只接收当前页候选的精确 ID，并复验所有安全条件。
- 删除成功后再写 checkpoint；checkpoint 写失败时允许从旧 cursor 安全重扫相关区间。
- 对空页、稀疏 ID、并发状态变化、部分删除、删除失败和 checkpoint 失败定义行为。
- 监控扫描数、候选数、删除数和耗时；持续低候选率时重新评估索引、分区或归档方案。

## Verification

- 原查询和主键扫描分别执行 `EXPLAIN`，证明选择主键扫描是基于真实执行计划，而不是猜测。
- 使用稀疏 ID 和空窗口验证 cursor 不会卡住或跳过后续记录。
- 删除失败时 checkpoint 保持不变；恢复后仍能处理同一页。
- 删除成功但 checkpoint 写失败时重跑，验证不会产生错误副作用。
- 扫描后改变候选状态，验证删除时的条件复验能够阻止误删。
- 插入高于当前 cursor 的新记录，验证 execution bound 和 sweep bound 不会让单次任务失控。
- 构造低候选密度数据，确认扫描放大仍在数据库容量预算内。

## Relationships

- [带 owner 校验与主动续期的分布式租约](./renewable-owner-checked-lease.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
