---
type: Pattern
title: 面向完整生命周期的软删除唯一性
description: 先决定业务标识是否允许删除后复用，再用 active-only unique constraint 或非布尔 delete token 保护 create、delete、recreate 与 restore 的完整生命周期。
resource: https://gitlab.example.com/example-org/iam/iam-vehicle-service/-/merge_requests/68
tags: [database, consistency]
---

# 面向完整生命周期的软删除唯一性

软删除字段与业务唯一键必须共同表达资源的生命周期。`is_delete = 0/1` 和“删除后写入自身主键”不是代码风格之争：前者适合标识永久保留或数据库能直接约束 active rows 的场景；后者是在缺少 partial unique index 的遗留模型中，让一个业务标识只对应一条有效记录、同时允许保留多条已删除历史记录的 delete token 技巧。

先决定业务标识能否在删除后复用，再选择索引和字段语义。不要先创建一个 Boolean `is_delete`，等唯一键冲突后再靠应用查询、异常重试或数据清理补救。

## Context

- 表使用 `is_delete`、`is_deleted` 或 `deleted_at` 保留历史行，普通查询只返回未删除记录。
- 手机号、用户名、外部 identifier、关系组合或其他业务键要求“同一时刻最多一条有效记录”。
- 业务可能执行 create → delete → recreate，也可能 restore 已删除记录。
- 数据库需要在并发 create、delete、rename 和 restore 下继续保护唯一性，应用层预查询不能成为最终约束。
- 目标数据库可能支持 partial / filtered unique index，也可能只能通过 generated column、functional index 或复合唯一键表达 active-only uniqueness。
- 既有字段可能名为 `is_delete`，但数据库已经写入主键值，ORM 却仍把它映射为 `Boolean`。

如果业务不需要保留历史、审计或恢复，应优先物理删除；不要为了统一表结构默认引入软删除。如果业务键天然永久保留，例如已签发且不可转移的外部 identity，也不应为了“方便重建”擅自释放唯一性。

## Problem

软删除只改变查询可见性，不会自动改变数据库唯一性。`UNIQUE(identifier)` 会让已删除行永久占用 identifier；如果应用创建前只查询 `is_delete = 0`，它会判断“可以创建”，随后在数据库插入时撞上历史行。

把索引改成 `UNIQUE(identifier, is_delete)` 也不一定正确。若 `is_delete` 只有 `0/1`，第一次删除产生 `(identifier, 1)`，重新创建产生 `(identifier, 0)`；第二次删除又试图产生相同的 `(identifier, 1)`，因此最多只能保存一条已删除历史。这个错误通常不会在普通 create / delete 测试中出现，而是在完整的 delete → recreate → delete 生命周期才暴露。

反过来，无条件规定“软删除必须把 `is_delete` 写成 id”也会混淆语义。若 identifier 永不复用，Boolean 已经足够；若数据库支持只约束有效行的唯一索引，使用真正的 `is_deleted` / `deleted_at` 加 active-only constraint 比把布尔字段改造成数字 token 更直接。

## Forces

- **标识复用策略**：删除后是永久占用、允许新记录复用，还是只允许恢复原记录。
- **历史保留数量**：同一业务键是否可能积累多条 deleted rows，保留多久，最终是否归档或清理。
- **数据库能力**：partial unique index、generated column、functional index、`NULL` 唯一性和在线 DDL 能力不同。
- **并发正确性**：多个实例可能同时 create、delete、rename 或 restore，预查询无法消除检查与写入之间的竞态。
- **字段真实性**：Boolean flag、时间戳、主键 token 和 tombstone version 的数据类型与含义不能混用。
- **恢复语义**：restore 可能与后来创建的 active row 冲突，不能默认把 deleted row 直接改回有效。
- **迁移风险**：既有 `is_delete = 1` 历史行、重复 active 数据、ORM 映射和唯一索引需要按同一发布顺序切换。
- **下游可见性**：CDC、缓存、搜索索引和审计查询需要区分 create、delete、recreate 与 restore，而不是只看到一个模糊布尔变化。

## Pattern

### 1. 先声明业务标识的生命周期契约

对每个 business key 明确选择以下一种语义。

#### 永久保留

删除后 identifier 仍属于原记录，不允许新记录复用。此时：

- 保留 `UNIQUE(identifier)` 跨全部历史行约束。
- `is_deleted BOOLEAN` 或 `deleted_at` 只表达可见性，不参与释放唯一性。
- create 的冲突检查必须包含已删除记录，并返回稳定的“标识已占用”业务错误。
- 若允许重新启用，只能走 restore / reactivate 原记录，并重新验证业务状态和权限。

#### 仅有效记录唯一

删除后允许新记录复用 identifier，同时保留任意多条历史行。此时数据库约束必须表达：同一规范化 identifier 最多一个 active row，deleted rows 不参与彼此冲突。优先使用数据库原生 active-only unique constraint；受遗留数据库能力限制时再使用 delete token。

无论选择哪一种，都要同时定义 rename、restore、merge、hard purge 和外部系统重新绑定时是否释放或重新占用 identifier。

### 2. 让数据库唯一约束成为并发终态 oracle

应用层 `exists` / `findActive` 只用于更早返回友好错误，不能证明随后 insert 仍然安全。create、rename 和 restore 必须由数据库 unique constraint 处理最终竞争：

- 写前使用与索引完全相同的规范化、字符集和 collation 语义。
- 捕获目标 constraint 的 duplicate-key error，并映射为稳定业务冲突；不要把所有数据库异常都改写成“已存在”。
- 并发 create 中只允许一个提交成功；失败方不得通过先删后插、覆盖写或无界重试绕过唯一性。
- delete 和 restore 使用条件更新与 rows-affected 判断实现幂等，不用先查状态再无条件 update。

索引约束的是事实，应用预查询只改善体验。两者必须检查同一个 business key scope；否则预查询成功、数据库失败会成为常态而不是竞态保护。

### 3. 优先使用 active-only unique constraint

数据库支持 partial / filtered unique index 时，直接只索引有效行。例如 PostgreSQL：

```sql
CREATE UNIQUE INDEX uniq_active_identifier
    ON resource (normalized_identifier)
    WHERE deleted_at IS NULL;
```

MySQL 可以使用 generated column 或受版本支持的 functional key part，把 deleted row 映射为 `NULL`，再利用 unique index 允许多个 `NULL` 的语义：

```sql
ALTER TABLE resource
    ADD COLUMN active_identifier VARCHAR(128)
        GENERATED ALWAYS AS (
            CASE WHEN is_deleted = 0 THEN normalized_identifier ELSE NULL END
        ) STORED,
    ADD UNIQUE INDEX uniq_active_identifier (active_identifier);
```

复合业务键可以生成 active key，或增加 `active_marker = CASE WHEN is_deleted = 0 THEN 0 ELSE NULL END` 并建立 `UNIQUE(key_part_1, key_part_2, active_marker)`。DDL 必须按实际数据库版本、索引长度、字符集、collation 与 generated column 限制验证，不把示例直接复制到未知环境。

不要直接建立 `UNIQUE(identifier, deleted_at)` 并把 active row 的 `deleted_at` 设为 `NULL`。允许多个 `NULL` 的数据库会因此允许多条 active rows，得到与目标相反的结果。

### 4. 遗留 MySQL 模型可使用非布尔 delete token

无法安全引入 active-only index、但需要保留多条 deleted history 时，可采用：

```sql
delete_token BIGINT NOT NULL DEFAULT 0,
UNIQUE KEY uniq_identifier_lifecycle (normalized_identifier, delete_token)
```

语义固定为：

- `delete_token = 0`：有效记录；复合唯一键保证同一 identifier 最多一条。
- `delete_token = id`：已删除记录；每行主键不同，因此同一 identifier 可保留多条历史。
- 主键必须稳定、非零且能无损写入 token 类型。

删除使用单条条件更新：

```sql
UPDATE resource
SET delete_token = id,
    deleted_at = CURRENT_TIMESTAMP
WHERE id = ?
  AND delete_token = 0;
```

这种字段不是 Boolean。新模型优先命名为 `delete_token` / `deleted_record_id`；若兼容遗留 schema 必须继续叫 `is_delete`，数据库类型、领域模型、序列化和 repository mapping 也必须使用整数，并在注释中明确 `0 = active, id = deleted`。`deleted_at`、`deleted_by` 仍作为独立审计字段存在，不让 token 同时承担时间和操作者语义。

不要用秒级时间戳或随机小整数代替主键 token：时间精度可能碰撞，随机值需要额外冲突处理，二者都不如已有唯一主键提供确定性。

### 5. 为 create、delete、recreate 与 restore 定义同一状态机

- **Create**：规范化 business key 后直接插入 active row；duplicate key 映射为稳定冲突。
- **Delete**：只把当前 active row 转成 deleted；重复删除根据 API 契约返回幂等成功或稳定 not-found，不再次改写 token。
- **Recreate**：创建新的主键和 active token；旧历史保持 deleted，不被覆盖或复用。
- **Restore**：尝试把目标历史行恢复为 active；如果 identifier 已被新 active row 占用，由唯一约束拒绝，并进入显式冲突处理，不能覆盖后来记录。
- **Rename**：在 active-only 唯一约束下更新规范化 identifier；与 create 使用同一 duplicate-key 语义。
- **Hard purge**：只按独立保留策略清理 deleted rows，不承担释放 active identifier 的正确性。

如果业务要求“删除后重建其实是恢复原实体”，就不要创建新 row；把它建模为 restore，并保留原主键、引用关系与审计轨迹。pattern 保护的是已声明的生命周期，不替业务决定 identity continuity。

### 6. 让查询、缓存和下游投影遵循相同状态语义

- 普通 repository 默认显式限制 active predicate；管理和审计查询通过独立方法包含 deleted rows，不靠调用方记住补条件。
- 缓存 key 与失效 scope 覆盖 create、delete、recreate、restore 和 rename；deleted old row 不能在新 active row 创建后重新填回缓存。
- CDC / event 包含 record id、business key、前后 lifecycle state 和版本，使下游能区分 delete、recreate 与 restore。
- 关联表不会因为主表软删除自动级联；必须单独声明关联保留、隐藏、解绑或清理语义。
- 所有 active-only 查询与唯一索引使用相同的 normalized key 和 active predicate，并用 `EXPLAIN` 验证主路径能够利用索引。

### 7. 把 schema、历史数据和应用映射作为一次迁移

从 Boolean `0/1` 迁移到 delete token 时：

1. 明确 identifier 是否允许复用，并扫描 active duplicates、历史冲突、`NULL`、大小写和规范化差异。
2. 引入能容纳主键的 `BIGINT` token 或 generated active key，不复用 `TINYINT(1)`。
3. 将所有 deleted rows 从 `1` 回填为各自行主键，active rows 保持 `0`；校验 token 唯一且无截断。
4. 同步修改 entity / DTO / repository mapping，删除 `Boolean` 假设和 `= 1` 查询。
5. 在数据满足约束后建立新 unique index，再切换 create、delete、restore 和 rename 写路径。
6. 用 schema introspection、行数对账和完整生命周期测试验证后，才移除旧索引或旧字段。

大表需要按数据库在线 DDL 能力制定发布、锁表、回滚和批量 backfill 方案。不要在不同发布中先改变字段含义、稍后再补唯一约束；中间窗口会让并发写入产生无法自动修复的数据。

## Failure Modes

- 把“软删除”直接等同于 `is_delete BOOLEAN`，没有定义业务标识删除后是否释放。
- `UNIQUE(identifier)` 约束全部历史行，但 create 只检查 active row，导致业务预检与数据库事实冲突。
- 使用 `UNIQUE(identifier, is_delete)` 加 `0/1`，只测试一次 delete / recreate，没有发现第二次 delete 会与第一条历史冲突。
- 数据库把 `is_delete` 写成主键，Java / ORM 仍映射为 Boolean，读取、序列化或条件查询把所有非零值压成同一状态。
- 仅用应用层 `SELECT` 检查唯一性，并发 create 或 restore 产生双 active rows。
- 使用 `UNIQUE(identifier, deleted_at)` 且 active `deleted_at = NULL`，误以为 `NULL` 会互相冲突。
- restore 无视后来创建的 active row，覆盖新实体或篡改 identity continuity。
- delete token 使用时间戳、随机值或窄整数，发生碰撞、截断或无法解释的重试结果。
- 迁移时把全部历史 `is_delete = 1` 原样转成 `BIGINT 1`，复合唯一键仍然只能容纳一条 deleted history。
- 先删除旧唯一索引再清理数据和建立新约束，留下并发写入多个 active rows 的无保护窗口。
- 默认认为软删除会级联到关联、缓存和搜索投影，导致旧关系或旧对象在下游继续可见。

## Implementation Checklist

- 声明每个 business key 是永久保留、active-only unique，还是仅允许 restore。
- 规范化、字符集、collation、`NULL` 与大小写语义在应用检查和数据库索引中一致。
- 数据库 unique constraint 是并发终态 oracle，预查询只用于友好错误。
- 优先 partial / filtered unique index 或 generated active key；受限遗留模型再使用 delete token。
- delete token 使用可容纳稳定非零主键的整数类型，不映射为 Boolean。
- create、delete、recreate、restore、rename 和 hard purge 都有显式状态与冲突语义。
- delete / restore 使用条件更新和 rows-affected 实现幂等。
- `deleted_at`、`deleted_by` 与 delete token 分工明确，不用一个字段承担所有审计信息。
- repository active predicate、缓存失效、CDC 和下游投影共享同一 lifecycle state。
- 迁移前扫描重复和历史值，回填 deleted token 后再建立约束并切换写路径。

## Verification

- 执行 create → delete → recreate → delete → recreate，验证始终最多一个 active row，且可保留多条 deleted history。
- 并发创建相同 normalized identifier，验证仅一个事务成功，其他请求返回目标 constraint 对应的稳定业务冲突。
- 并发执行 delete 与 recreate，验证提交顺序决定唯一结果，不出现双 active 或被覆盖的历史行。
- 重复 delete 同一记录，验证 token 不被再次改写，API 幂等语义稳定。
- 在 identifier 已被新记录占用时 restore 旧记录，验证 unique constraint 拒绝并进入显式冲突处理。
- 对大小写、空白、区号、Unicode normalization 或其他业务规范化边界，验证应用与索引看到同一 key。
- 迁移 fixture 包含多条 `is_delete = 1` 历史、active duplicate、`NULL` 和最大主键，验证 backfill 无冲突、无截断、无漏行。
- 回读 schema，确认字段类型、default、generated expression、index columns 与 active predicate 符合设计。
- 对 active lookup、create conflict probe 和历史查询运行 `EXPLAIN`，验证索引可用且不会退化为无界扫描。
- 重放 delete 前的缓存填充或下游事件，验证旧版本不能覆盖 recreate / restore 后的新 active 状态。

## Evidence

- 真实命中：[`iam-vehicle-service!68`](https://gitlab.example.com/example-org/iam/iam-vehicle-service/-/merge_requests/68) 新增 identifier 唯一键时仍使用 `TINYINT(1)` / Boolean 软删除；active-only 预查询与历史行唯一约束不一致，完整 delete → recreate 生命周期需要在“永久占用”与“active-only unique”之间明确选择。
- 真实命中：[`iam-li-partner-service@227642d` schema](https://gitlab.example.com/example-org/idaas/iam-li-partner-service/-/blob/227642de495ba113a34e60f6ea97d9606b40551d/sql/00_schema.sql#L26-41) 使用 `BIGINT is_delete` 和多组 `UNIQUE(business_key, is_delete)`，[删除实现](https://gitlab.example.com/example-org/idaas/iam-li-partner-service/-/blob/227642de495ba113a34e60f6ea97d9606b40551d/src/main/java/com/lixiang/iam/lipartner/repository/impl/UserRepositoryImpl.java#L363-372) 将 token 写为行主键，独立证明该结构可同时保留历史与释放 active business key。
- 独立复现次数：2 个服务仓库分别提供失败命中与既有实现，并共同覆盖唯一索引、字段类型、删除写路径和重复生命周期。
- 可迁移性判断：该模式适用于需要软删除且存在 business uniqueness 的关系数据库表；无唯一业务键、物理删除或数据库已由其他 authority 管理生命周期时不迁移。identifier 永久保留时采用 Boolean / 全历史唯一分支，不迁移到 active-only index 或 delete token。

## References

- [MySQL CREATE INDEX Statement](https://dev.mysql.com/doc/refman/8.4/en/create-index.html)：说明 unique index 的复合 key 与多个 `NULL` 值语义。
- [MySQL Optimizer Use of Generated Column Indexes](https://dev.mysql.com/doc/refman/8.4/en/generated-column-index-optimizations.html)：说明 generated column 可建立并使用索引。
- [PostgreSQL Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html)：说明通过 predicate 建立 partial unique index，只约束满足条件的 rows。

## Relationships

- [基于主键扫描的破坏性清理](./primary-key-sweep-for-destructive-cleanup.md)
- [按操作定义一致性与分区契约](./operation-scoped-consistency-contract.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
