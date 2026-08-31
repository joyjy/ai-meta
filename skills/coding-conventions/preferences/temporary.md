# Temporary Pitfalls

本文件只保存短期有效、已有明确命中信号的个人工程提醒。Agent 仅在 Scope / Signals 命中且当前日期不晚于 Expires 时应用；到期条目不再生效，并应提示清理或基于重复证据晋升为长期模板规则。

## Reactor API 与 Gradle dependency constraint 不兼容

- Status: temporary
- Scope: Java / Gradle / Spring Boot / Reactor，尤其是使用 `li-boot` 构建约束的服务
- Expires: 2026-08-03
- Signals: 服务启动出现 `NoSuchMethodError`、缺失符号为 `Scheduler.disposeGracefully()`，或运行时解析到 `reactor-core 3.4.19`
- Pitfall: 不要只看或覆盖业务服务声明的直接依赖；Gradle plugin、BOM 或 dependency-management constraint 可能改写最终运行时版本。本次事故最终定位到 Gradle plugin 依赖约束将 `reactor-core` 固定为 `3.4.19`。
- Probe: 运行 `./gradlew dependencyInsight --dependency reactor-core --configuration runtimeClasspath`，并检查 Spring Boot plugin、BOM 与 dependency-management 来源。
- Known baseline: 本次事故中 Spring Boot `2.7.18` 对应的 `reactor-core 3.4.34` 已验证兼容；不要把该版本组合外推为所有项目的永久要求。
- Verify: 以 resolved runtime graph 为准确认 Reactor 版本，再执行服务启动 smoke，确保不再出现对应 `NoSuchMethodError`。
- Evidence: [`example-org/build!454`](https://gitlab.example.com/example-org/build/-/merge_requests/454/diffs) 及 2026-07-20 群聊更正说明

## 目标 SQL 方言能力先验证

- Status: temporary
- Scope: 为既有数仓、运维查询平台或不透明 SQL 执行环境生成查询，尤其涉及日期函数、字符串下标、行构造、隐式时间解析或派生表语法时
- Expires: 2026-09-04
- Signals: 目标引擎 / 版本不明确；同项目没有已验证 SQL；准备首次使用 `DATE`、`STACK`、`SUBSTR` 下标、隐式 `UNIX_TIMESTAMP`、日期算术或复杂派生表
- Pitfall: 不要把通用 MySQL、Hive 或 Spark SQL 语法直接当作目标环境事实；相同函数名也可能缺失、下标不同或解析语义不同，容易得到报错或更危险的静默漏数。
- Probe: 先从同项目已成功 SQL 或目标平台文档确认方言；仍不确定时，用一条只验证单个函数 / 边界的最小只读查询，再组合业务 SQL。
- Verify: 用一个已知时间 / ID 样本证明过滤能命中，并核对总数、分组和时间边界；结果为 0 时先验证方言与时区，不直接解释为没有数据。
- Evidence: `preferences/pitfall-watch.md` 中 `sql.target-dialect.features-unverified` 的 2026-08-01 与 2026-08-05 两次独立命中
