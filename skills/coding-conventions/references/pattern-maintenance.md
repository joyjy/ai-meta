# Pattern Maintenance

只在新增、更新、晋升或调整 coding-conventions pattern 与 label 时读取。普通 pattern 使用直接从主 skill 路由到命中的 `../patterns/<id>.md`，不要先读本文件，也不要递归加载 Related 条目。

## Ownership

- `../templates/` 保存跨项目默认成立、适合直接约束实现和验证的共享规则。
- `../preferences/` 保存个人取舍，只进入个人默认层。
- `../patterns/` 保存仅在特定 forces 成立时采用的工程解法，不作为无条件规则注入 `AGENTS.md`。

## Admission

1. 只有问题具有可重复场景、明确 forces、可辨认的解法结构和真实失败模式时才写 pattern。无条件底线回模板，个人取舍回 preferences，一次性事故或任务状态不进入 pattern。
2. 每个正式 pattern 单独成 OKF concept 文件，至少包含 Context、Problem、Forces、Pattern、Failure Modes、Implementation Checklist 和 Verification。
3. 正文默认使用中文并面向人类读者，保留必要英文 ID、技术术语与 API；只保留可迁移的当前解法，不写完整事故复盘。
4. 真实 MR、issue 或代码只作为 evidence anchor。候选只保留证据入口和一句待提炼主题，不提前写成结论。
5. 晋升至少需要 `KNOWN` evidence anchor；重复性需要 `COMPUTED` 独立命中，适用范围需要带 supporting evidence 的 `INFERRED`。主入口会同时加载 evidence classification；不得仅凭 `COMMON`、`FRAME` 或 `GUESS` 晋升。
6. 新增正式条目时同步更新主 skill 的 Pattern Routes；其中只保留 ID、可辨认 signal 与 exact path。

## OKF And Labels

- 非 reserved pattern 文件必须有可解析 YAML frontmatter 和非空 `type`；label 使用 OKF `tags`，不新增 `labels` 等私有字段。
- 新增或调整 label 时，主入口会同时加载 `../patterns/label.md`；按实际检索摩擦回顾，不预设固定数量、分类轴或封闭词表。
- Pattern 文件可保留 Related 链接供人阅读，但 agent 普通加载到目标 pattern 后停止，不沿链接展开。
