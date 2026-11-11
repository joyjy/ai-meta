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

## Decision Graph

- 选型类 pattern 可以把 Pattern 节写成 Mermaid 决策图。适用条件：存在互斥方案，且选择前须先回答约束事实或业务偏好。流程、核对清单和概念框架不画图。
- 读图与执行规则由主 skill 的「决策图 pattern」持有，pattern 内不复制。
- 节点 ID 用稳定 ASCII。问题标签保持短，使用英文标点。完整含义写在 Forces，并标注节点 ID。
- 每个问题节点都有「未知」分支，指向 `S0` 或 `S1`。业务偏好节点用 `{{ }}`。
- 单图不超过约 15 个节点。独立维度分成多张图，用同一个连接节点衔接。超出规模时拆成独立 pattern，用 `[[pattern-id]]` 连接。
- 图要有入口节点和终点。策略节点在说明表中写动作、收益、接受的风险／成本和必须守住。平台或版本核对挂到对应节点下，Verification 条目标注适用节点。
- 新增或调整后，确认图可被 Mermaid 解析，并核对节点 ID 与说明表双向一致。
- 只为有可迁移证据的失败补规则。单个样本暴露的问题先记录，不直接写成规则或示例。

## OKF And Labels

- 非 reserved pattern 文件必须有可解析 YAML frontmatter 和非空 `type`；label 使用 OKF `tags`，不新增 `labels` 等私有字段。
- 新增或调整 label 时，主入口会同时加载 `../patterns/label.md`；按实际检索摩擦回顾，不预设固定数量、分类轴或封闭词表。
- Pattern 文件可保留 Related 链接供人阅读，但 agent 普通加载到目标 pattern 后停止，不沿链接展开。
