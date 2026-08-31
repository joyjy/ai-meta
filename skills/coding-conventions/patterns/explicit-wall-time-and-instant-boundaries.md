---
type: Pattern
title: 显式区分墙上时间与时间点
description: Java / JDBC 服务持久化 MySQL 时间时，先区分 wall time 与 instant，再显式约束应用类型、连接时区、字段语义和跨服务边界。
resource: https://dev.mysql.com/doc/connector-j/en/connector-j-time-instants.html
tags: [database]
---

# 显式区分墙上时间与时间点

MySQL `DATETIME` 保存的是不带时区的日历字段，可以把它理解为“墙上时间”：写入什么年月日时分秒，数据库就保存和返回什么年月日时分秒。它本身不能说明这个值属于 UTC、`Asia/Shanghai`，还是其他时区。

JDBC 只有在 Java 时间对象、SQL 类型和驱动配置需要完成 instant 与 wall time 映射时才做时区转换。转换结果可能受 JVM 默认时区、`serverTimezone` / `connectionTimeZone`、session `time_zone`、Connector/J 版本以及 `preserveInstants` 等配置影响；连接串中的时区不等于数据库会无条件转换所有时间，也不保证 MySQL session 时区已经被修改。

## Terminology

在设计、字段命名和评审中固定使用以下概念，避免用含混的“本地时间”“UTC 时间”代替不同语义：

- **Instant（时间点）**：时间线上的唯一时刻，与地区无关。应用层通常用 `Instant` / `OffsetDateTime` 表达，协议使用 ISO-8601 `Z` / offset。
- **UTC storage value（UTC 存储值）**：instant 的规范持久化表示。它可以存入 `TIMESTAMP`，也可以按应用契约编码成 `DATETIME` 的 UTC 日历字段；后者的 UTC 语义来自应用契约，不来自字段类型。
- **Wall time（墙上时间）**：某地日历和时钟显示的年月日时分秒，例如“2026-07-15 09:00”。它本身不能定位唯一 instant。
- **Stored offset（存储偏移）**：解释遗留 wall time 型 `DATETIME` 时必须附加的 offset。例如 `2026-07-15 11:42:31` + `+08:00` 才能还原成 instant。它描述数据当初如何编码，不描述用户现在应该如何显示。
- **Zone ID（时区规则标识）**：IANA 时区名，例如 `Asia/Shanghai`、`Europe/Berlin`。它包含历史和未来的 offset / DST 规则。
- **Operating zone（节点业务时区）**：一个独立节点、租户或数据分区归属的 Zone ID。它决定本地业务日、默认展示时间和“每天 09:00”一类调度如何解析。
- **Display zone（展示时区）**：当前管控面或用户选择用来渲染 instant 的 Zone ID。没有显式用户偏好时，默认使用目标数据的 operating zone，而不是管控面服务器时区。
- **Resolved offset（解析后偏移）**：某个 Zone ID 在某个 instant 上解析出的 offset，例如 `+08:00`。它适合传输或记录某次显示结果，但不能替代 Zone ID 计算未来调度。
- **Locale（区域格式）**：语言、日期格式、数字格式等展示规则，例如 `zh-CN`；它不决定 timezone。

## Context

- Java 服务通过 JDBC / Connector/J 读写 MySQL `DATETIME` 或 `TIMESTAMP`。
- 业务代码使用 `Instant`、`Date`、`Timestamp`、`LocalDateTime` 或带 offset 的时间类型。
- 多个服务、多个 JVM 时区或新旧写入方共享同一时间字段。
- 系统同时存在“某个真实时间点”和“某地日历时间”两类业务语义。
- 统一管控面读取多个独立节点的数据，并需要按数据归属地展示时间或保证本地调度准点执行。

## Problem

字段名通常只有 `create_time`、`execute_time` 或 `effective_time`，无法说明它保存的是时间点还是墙上时间。开发者容易把 `DATETIME` 当成自动存 UTC 的时间点，或认为 JDBC URL 里的时区会统一修正数据库中的所有值。

当两个写入方分别按 UTC 和 GMT+8 把同一 instant 渲染成 `DATETIME` 时，同一列会出现相差 8 小时的两种语义。数据库只能看到两组合法的日历数字，无法自行判断或修复。

## Forces

- `DATETIME` 不携带 offset / zone，适合保存日历字段，但不能独立表达真实时间点。
- `TIMESTAMP` 由 MySQL 按 session 时区与 UTC 互转，能够表达时间点，但显示结果仍受读取 session 时区影响。
- `LocalDateTime` 表达墙上时间；`Instant`、`OffsetDateTime` 等表达或携带时间点语义，两者不能靠命名互换。
- Connector/J 行为受驱动版本、Java 类型、目标 SQL 类型及连接配置共同影响，不能只读一个 `serverTimezone` 参数下结论。
- 历史表可能已经混入多种写入语义，直接全表加减固定小时数会破坏其中一部分正确数据。

## Pattern

先为每个时间字段选择一种明确语义：

```text
真实时间点（instant）
  → 应用内使用 Instant / OffsetDateTime
  → API 携带 Z 或 offset
  → 持久化层统一约定 UTC，或使用可保留 instant 的 TIMESTAMP 映射

业务墙上时间（wall time）
  → 应用内使用 LocalDateTime
  → 另有明确的 ZoneId / 业务地域上下文
  → DATETIME 原样保存日历字段
```

统一存储 UTC 只解决跨节点排序、比较和传输，不自动解决本地展示与本地调度：

```text
管控面展示
  UTC storage value + 目标数据的 operating zone
  → 解析该 instant 的 resolved offset
  → 得到当地 wall time

未来本地调度
  scheduled wall time + operating zone
  → 按 Zone ID 的规则解析
  → 得到下一次 scheduled instant
```

节点级多时区部署且数据独立存储时，在节点 / 租户 / 数据分区元数据中维护 `operating_zone_id`。事件表继续保存 UTC instant；统一管控面读取数据时同时取得其 operating zone，再转换成当地 wall time。只有单条事件可能脱离节点默认时区，或必须永久保留事件发生时采用的时区规则时，才在事件上额外保存 `origin_zone_id`，必要时再保存当时的 `origin_offset`。

管控面若允许用户选择个人展示时区，可另设 `display_zone_id`；它只影响显示，不改变数据归属和调度语义。默认 display zone 应来自目标节点的 operating zone，不能来自管控面进程或数据库连接的默认时区。

固定 `+08:00` 能把某个 instant 显示为上海当前墙上时间，但 offset 不包含 DST 和未来规则，不能用于表达“欧洲节点每天本地 09:00”一类调度。未来调度必须保存 wall time 与 Zone ID，并在每次计算下一执行时间时解析成 instant。

如果使用 `DATETIME` 保存 UTC instant，必须把“该列中的日历数字统一代表 UTC”定义为应用层契约，并保证所有写入方在绑定 JDBC 参数前都生成 UTC wall time。数据库类型本身不会提供这项保证。

连接配置应显式记录并验证三件事：JVM 默认时区、Connector/J 的 connection time zone，以及 MySQL `@@SESSION.time_zone`。不要假设设置 `serverTimezone` 就一定修改 session；需要修改 session 时，使用与当前 Connector/J 版本匹配的明确配置并通过查询验证。

面对已经混合的历史 `DATETIME`，先按写入方、写入版本、审计事件或可靠 cutover 边界识别语义。无法识别的记录保持原值，并在业务边界上采取保守策略；不要直接执行全表固定时差转换。

如果必须给仍由多种时区语义写入的遗留 `DATETIME` 增加解释元数据，字段应表达 stored offset，例如与 `create_time`、`update_time` 分别对应的 `create_time_offset`、`update_time_offset`。不要把它命名成 `display_offset`，也不要用 `_at` 后缀表示一个 offset。每个时间字段可能由不同写入方产生，不能只用一个行级 offset 解释整行。

## Failure Modes

- 把 `DATETIME` 当作自带 UTC / 时区的字段，读取后直接构造成 `Instant`。
- 把解释遗留 `DATETIME` 的 stored offset 当成管控面 display offset，同一个值同时承担解码与展示职责。
- 认为 JDBC URL 中出现 `serverTimezone=UTC` 就代表数据库中的所有时间都会自动转换为 UTC。
- 使用 JVM 默认时区完成关键业务转换，使容器、开发机和测试环境得到不同结果。
- 同一列由 UTC 与本地时区写入方共同写入，却仍按单一时区解释全部历史记录。
- 将 locale 与 timezone 绑定，例如因为语言是中文就隐式选择 GMT+8。
- 管控面用自身 JVM / 浏览器时区展示所有节点的 UTC instant，使其他节点看起来在错误时间执行。
- 只保存固定 display offset 并用它计算未来周期调度，在 DST 切换后提前或延后一小时。
- 对混合语义的历史 `DATETIME` 全表统一加减 8 小时。

## Implementation Checklist

- [ ] 标明字段表达 instant 还是 wall time，以及选择该语义的业务原因。
- [ ] instant 在应用层优先使用 `Instant` / `OffsetDateTime`，wall time 使用 `LocalDateTime` 并显式保留业务 `ZoneId`。
- [ ] API 中的 instant 使用 ISO-8601 `Z` / offset，不传递无时区字符串冒充时间点。
- [ ] 独立节点 / 租户 / 数据分区维护明确的 `operating_zone_id`，统一管控面展示默认使用数据归属 zone。
- [ ] 用户选择的 `display_zone_id` 只影响展示，不覆盖节点 operating zone 或调度规则。
- [ ] 周期调度保存 wall time + Zone ID；resolved offset 只作为某个 instant 的派生结果。
- [ ] 显式配置并记录 JVM 时区、Connector/J connection time zone 和 MySQL session 时区。
- [ ] `DATETIME` 保存 instant 时，声明统一 UTC 的应用层契约并审计所有写入方。
- [ ] 遗留 mixed-timezone `DATETIME` 若增加 stored offset，按时间字段分别维护，并保证每次对应写入都会更新，不能只依赖 INSERT default。
- [ ] 多写入方共享表时，确认它们使用相同 Java 类型、驱动语义和时区约定。
- [ ] 历史迁移前先找到写入来源或可靠 cutover；没有证据时不做固定时差批量修正。

## Verification

- [ ] 在连接建立后查询 `NOW()`、`UTC_TIMESTAMP()`、`@@GLOBAL.time_zone`、`@@SESSION.time_zone` 和 `@@system_time_zone`，保存真实运行证据。
- [ ] 用同一个已知 instant 分别通过目标 Java 类型和 JDBC 配置写入测试记录，核对数据库原始 `DATETIME` / `TIMESTAMP` 值。
- [ ] 在 UTC 与非 UTC JVM 中读取同一记录，验证 instant 是否保持同一时间点、wall time 是否保持同一日历字段。
- [ ] 从统一管控面读取两个 operating zone 不同但 instant 相同的节点事件，验证各自显示正确的当地 wall time。
- [ ] 跨 DST 切换计算“每天本地 09:00”的下一执行时间，验证 wall time 不漂移且 instant 按规则变化。
- [ ] 验证 `serverTimezone` / `connectionTimeZone` 是否真的改变了 session，而不是只改变驱动的解释方式。
- [ ] 对共享表逐个确认活跃写入方，并用日志时间与数据库原始值建立至少一条端到端证据。

## Relationships

- [MySQL Connector/J：Preserving Time Instants](https://dev.mysql.com/doc/connector-j/en/connector-j-time-instants.html)
- [MySQL Server Time Zone Support](https://dev.mysql.com/doc/refman/8.0/en/time-zone-support.html)
- [coding-conventions](../SKILL.md)
