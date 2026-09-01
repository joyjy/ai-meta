# Temporary Pitfalls

本文件只保存短期有效、已有明确命中信号的个人工程提醒。Agent 仅在 Scope / Signals 命中且当前日期不晚于 Expires 时应用；到期条目不再生效，并应提示清理或基于重复证据晋升为长期模板规则。

## 目标 SQL 方言能力先验证

- Status: temporary
- Scope: 为既有数仓、运维查询平台或不透明 SQL 执行环境生成查询，尤其涉及日期函数、字符串下标、行构造、隐式时间解析或派生表语法时
- Expires: 2026-09-04
- Signals: 目标引擎 / 版本不明确；同项目没有已验证 SQL；准备首次使用 `DATE`、`STACK`、`SUBSTR` 下标、隐式 `UNIX_TIMESTAMP`、日期算术或复杂派生表
- Pitfall: 不要把通用 MySQL、Hive 或 Spark SQL 语法直接当作目标环境事实；相同函数名也可能缺失、下标不同或解析语义不同，容易得到报错或更危险的静默漏数。
- Probe: 先从同项目已成功 SQL 或目标平台文档确认方言；仍不确定时，用一条只验证单个函数 / 边界的最小只读查询，再组合业务 SQL。
- Verify: 用一个已知时间 / ID 样本证明过滤能命中，并核对总数、分组和时间边界；结果为 0 时先验证方言与时区，不直接解释为没有数据。
- Evidence: 2026-08-01 AMP 内审 SQL 与 2026-08-05 endpoint 生产数据分析两次独立命中（2 sessions / 2 projects）
