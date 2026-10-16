# Pattern Maintenance

只在新增、更新、晋升或调整 coding-conventions pattern 与 label 时读取。普通 pattern 使用直接从主 skill 路由到命中的 `../patterns/<id>.md`，不要先读本文件，也不要递归加载 Related 条目。

## Ownership

- `../templates/` 保存跨项目默认成立、适合直接约束实现和验证的共享规则。
- `../preferences/` 保存个人取舍，只进入个人默认层。
- `../patterns/` 保存从场景出发的检查与决策 SOP。入口描述任务事实，正文先检查前提，再选择解法；不把某种实现作为命中场景后的必选答案。

## Admission

1. 只有问题具有可重复场景、明确 forces、可辨认的解法结构和真实失败模式时才写 pattern。无条件底线回模板，个人取舍回 preferences，一次性事故或任务状态不进入 pattern。
2. 每个正式 pattern 单独成 OKF concept 文件，至少包含 Context、Problem、Forces、Pattern、Failure Modes、Implementation Checklist 和 Verification。
3. 正文默认使用中文并面向人类读者，保留必要英文 ID、技术术语与 API；只保留可迁移的当前解法，不写完整事故复盘。
4. 真实 MR、issue 或代码只作为 evidence anchor。候选只保留证据入口和一句待提炼主题，不提前写成结论。
5. 晋升至少需要 `KNOWN` evidence anchor；重复性需要 `COMPUTED` 独立命中，适用范围需要带 supporting evidence 的 `INFERRED`。主入口按晋升条件读取 [证据分类](../../../docs/reference/evidence-classification.md)；不得仅凭 `COMMON`、`FRAME` 或 `GUESS` 晋升。
6. 新增或调整条目时，同步主 skill 的 Pattern Routes。触发写“新增／修改什么”，不要求 agent 先知道存在某个缺陷或已选择某个方案。
7. 按义务分层，不按文件名机械分类。默认交付要求归对应模板；条件必查由主入口声明场景和检查点。具体解法保留在 pattern 内按 forces 选择。一份正文可同时包含必查问题和可选解法，不因此整篇升级成强制实现。
8. 每条路由保留适用场景、exact path 和必要的排除条件。检查简单方案已足够、用户另有明确约束和缺少执行授权的反例。不新增全量预读、平行目录索引或固定测试矩阵。

## OKF And Labels

- 非 reserved pattern 文件必须有可解析 YAML frontmatter 和非空 `type`；label 使用 OKF `tags`，不新增 `labels` 等私有字段。
- 新增或调整 label 时，主入口会同时加载 `../patterns/label.md`；按实际检索摩擦回顾，不预设固定数量、分类轴或封闭词表。
- Pattern 文件可保留 Related 链接供人阅读，但 agent 普通加载到目标 pattern 后停止，不沿链接展开。
