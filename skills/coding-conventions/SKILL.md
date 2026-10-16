---
name: coding-conventions
description: 在代码实现、调试、验证或评审中主动识别工程模板与可复用 pattern；也用于 cc、consumer pattern、consumer replay、消费后内部重放，跳板机脚本交付，以及约定初始化 / 校验、偏好与 pitfall 维护、范式提炼和数仓建模。
---

# coding-conventions

## Routing

- 新增、修改或评审自有 CLI：读取 `templates/cli/AGENTS.md`；涉及 `usage` 实现时，同读 `patterns/cli-usage-observability.md`。不以项目缺少 CLI 受控块或尚无统计需求为由跳过。
- 选择验证方式、新增或保留测试、执行测试减法时，先读 `templates/testing/AGENTS.md` 的准入与保留标准。项目明确要求的检查继续执行。
- 已有 `coding-conventions:begin <template-id>`：读取对应模板作为受控块事实源；用户明确指令与更高层执行边界优先。报告 unsupported ID 或缺失模板。
- 无受控块但要实现、调试、验证或评审：按技术栈读模板；团队 / 外部项目不加载 `preferences/*`。
- 用户提到 `consumer pattern`、`consumer replay` 或“消费后内部重放”时，先读取 `patterns/consumer-owned-retryable-execution-unit.md`，按其定义判断当前实现与适用性；用户明确指定其他定义时遵从该定义。普通 `consumer` 一词仍按下方场景信号路由。
- 按 Pattern Routes 用当前任务场景定位 SOP。先检查事实和约束，再选择解法；不等识别出缺陷或选好技术才加载，不预读无关正文或递归 Related。
- 代码实现：读取 `references/structural-checkpoints.md`，按行为阶段执行结构检查。
- 创建或清理 Git worktree：读取 `references/worktree-lifecycle.md`。
- 初始化、注入模板、配置 hook 或接入 `node-test-kit`：读 `references/project-initialization.md`，按已授权目标扫描；范围未定时展示候选并确认。只读校验工程约定和验证能力时读 `references/project-audit.md`。
- 维护 pitfall：读 `references/pitfall-maintenance.md`；候选只读 `preferences/pitfall-watch.md` 的相关 signature；晋升同读 `../../docs/reference/evidence-classification.md`。
- 维护 pattern：读 `references/pattern-maintenance.md`；晋升时同读 evidence classification；调整 label 才读 `patterns/label.md`。
- 目标 SQL 方言不明，或首次使用日期、字符串、行构造等方言特性：读 `preferences/temporary.md` 的对应未过期条目。
- 用户要求跳板机执行、无法 scp、编码加剪贴板或分批名单交接：读取 `preferences/bastion-script-handoff.md`。用于个人手工交付，不注入团队源码。
- 用户要求生成供后台手工执行的 SQL：读取 `preferences/sql.md`。这是个人交付偏好，不注入团队项目，不用于约束项目源码中的 SQL。
- IDaaS 行为变更：读 `preferences/lintest-walkthrough.md`。
- 创建或更新 MR/PR、准备正式回归或合并前：读 `templates/git/AGENTS.md` 的目标分支同步约定。处理 Git 合并冲突、stacked branch 同步或批量选择 ours/theirs 时，同读其合并核验约定。

## Ownership Boundaries

- 工程规则归本 skill，任务归 `gtd`，执行分流归 `agent-assignment`，工具路线摩擦归 `~/.ai/agent-frictions.md`。
- `templates/` 可注入项目；`preferences/` 只进个人层；`patterns/` 只在 forces 命中时读取。UI 方向归 `design-direction`，只从已解析的个人 project root 读 `DESIGN.md`；GitLab flow 和 MR baseline 归 tool routes、context / exit skills 与项目 `index.md`。

## Template Routes

模板位于 `templates/<id>/AGENTS.md`：`general`、`api`、`testing`、`git`、`node-test-kit`、`java-gradle`、`python`、`cli`、`frontend`、`lintest`。`general` 是默认基线；父级已有受控块时子项目不重复，只加载有 repo 证据的模板。

## Pattern Routes

按“正在新增、修改或评审什么”匹配当前变更域，不以已经诊断出风险为前提。只加载命中场景的 SOP；正文先检查前提，再选择或排除方案。模板底线、条件检查和可选解法分开，不把整份实现或验证清单变成通用要求。

### 默认要求

- 自有 CLI 的 `usage`：准入由 `templates/cli/AGENTS.md` 持有，实现时读 `patterns/cli-usage-observability.md`。
- 简单 UI 提交的 pending、结果反馈和重复触发保护：执行 `templates/frontend/AGENTS.md`，不因此加载整套交互协调方案。

### 条件必查 SOP

- 改变线程池、后台队列或 consumer / listener 的资源装配、准入或启停：`patterns/graceful-shutdown-anti-leak.md`。先查资源归属与退出边界；仅改业务字段不触发。
- 多阶段 UI、连续输入请求协调、并发或后台回写、乐观更新及 Undo：`patterns/ui-interaction.md`。先查交互冲突；纯布局和简单提交不触发。
- 同时存在软删除与业务唯一键，且本次改变其创建、删除、重建或恢复：`patterns/lifecycle-safe-soft-delete-uniqueness.md`。先定标识复用政策，不预选 delete token。
- 新增或改变分布式锁／租约保护的任务：`patterns/renewable-owner-checked-lease.md`。先查库的续期、释放与失锁语义，已覆盖时复用。
- 建设或调整分析模型、共享指标、数仓层或回刷：`patterns/business-process-first-warehouse-modeling.md`。先定粒度和消费契约，不要求完整分层。
- 改变 Java / JDBC 时间持久化、跨时区展示或本地周期调度：`patterns/explicit-wall-time-and-instant-boundaries.md`。先定时间语义；普通时间类型引用不触发。
- 首次接入外部 API / SDK，或改变版本、端点及响应处理：`patterns/vendor-api-contract-preflight.md`。先核对已有 adapter 和契约证据；普通调用已验证入口不重做预检。
- 新增缓存或改变缓存读取、写入、删除与失效链路：`patterns/authority-first-cache-consistency.md`。先查实际复用、机制必要性、权威提交与失效覆盖，不默认叠加准入、TTL 或观测。
- 跨进程、存储或区域的状态设计，按当前待决问题选一份，不整组加载：
  - 谁接收、谁提交、谁排序、谁保存副本：`patterns/authority-ordering-replication-separation.md`。
  - 成功响应证明什么、读取何时可见、超时如何处理：`patterns/operation-scoped-consistency-contract.md`；具体缓存问题走缓存 SOP。
  - 故障时要守住什么、允许什么、如何恢复：`patterns/failure-model-first-distributed-state-design.md`。机制尚未选择时也适用。

### 可选解法的场景入口

以下 SOP 用来作选择，不表示必须采用同名实现。先完成前提检查；不适用时沿用已有简单方案，不为匹配 pattern 改造需求。

- Consumer 业务动作需要按对象补做、重试或 backfill：`patterns/consumer-owned-retryable-execution-unit.md`。先查现有恢复入口和最小业务输入，不默认增加人工 API 或 Inbox。
- 批量清理持久数据、调整扫描／删除／checkpoint：`patterns/primary-key-sweep-for-destructive-cleanup.md`。先查索引与执行边界；已有合适索引优先使用，不预设全表主键扫描。
- 多区域统一入口、各区本地读，同时不允许冲突合并：`patterns/single-writer-forwarding-edge-replica.md`。先比较现有事务／托管存储能力和分区要求；不预设单写转发拓扑。

## Safety Gates

- 写入须有明确目标与范围；复用用户已有授权。新增未授权模板、hook 或构建集成时，先展示具体改动再确认。
- 团队 / 外部项目不注入个人路径、私有 helper 或 `preferences/*`。
- 不临场编写模板外 hook。已提供 partial 也要先在目标 repo 验证命令并披露目标与行为；复用已明确的 hook 授权，只有范围未定时才确认。
- pattern/pitfall 晋升按对应 reference 保留可核验 evidence；一次性事故不进长期模板。

## Completion Standard

按选中模板实际验证；注入或 audit 验收由命中的 direct reference 负责。
