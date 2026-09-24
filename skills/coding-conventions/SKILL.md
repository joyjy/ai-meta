---
name: coding-conventions
description: 在代码实现、调试、验证或评审中主动识别工程模板与可复用 pattern；也用于约定初始化 / 校验、偏好与 pitfall 维护、范式提炼和数仓建模。
---

# coding-conventions

## Routing

- 已有 `coding-conventions:begin <template-id>`：读取对应模板作为受控块事实源；用户明确指令与更高层执行边界优先。报告 unsupported ID 或缺失模板。
- 无受控块但要实现、调试、验证或评审：按技术栈读模板；团队 / 外部项目不加载 `preferences/*`。
- 代码任务按 Pattern Routes 命中信号读取并检查 forces，不预读或递归 Related。
- 初始化、注入模板、配置 hook 或接入 `node-test-kit`：读 `references/project-initialization.md`，按已授权目标扫描；范围未定时展示候选并确认。只读校验工程约定和验证能力时读 `references/project-audit.md`。
- 维护 pitfall：读 `references/pitfall-maintenance.md`；候选只读 `preferences/pitfall-watch.md` 的相关 signature；晋升同读 `../engineering-exit/references/evidence-classification.md`。
- 维护 pattern：读 `references/pattern-maintenance.md`；晋升时同读 evidence classification；调整 label 才读 `patterns/label.md`。
- 目标 SQL 方言不明，或首次使用日期、字符串、行构造等方言特性：读 `preferences/temporary.md` 的对应未过期条目。
- IDaaS 行为变更：读 `preferences/lintest-walkthrough.md`。
- 处理 Git 合并冲突、stacked branch 同步或批量选择 ours/theirs：读 `templates/git/AGENTS.md` 的合并核验约定。

## Ownership Boundaries

- 工程规则归本 skill，任务归 `gtd`，执行分流归 `agent-assignment`，工具路线摩擦归 `~/.ai/agent-frictions.md`。
- `templates/` 可注入项目；`preferences/` 只进个人层；`patterns/` 只在 forces 命中时读取。UI 方向归 `design-direction`，只从已解析的个人 project root 读 `DESIGN.md`；GitLab flow 和 MR baseline 归 tool routes、context / exit skills 与项目 `index.md`。

## Template Routes

模板位于 `templates/<id>/AGENTS.md`：`general`、`api`、`testing`、`git`、`node-test-kit`、`java-gradle`、`python`、`cli`、`frontend`、`lintest`。`general` 是默认基线；父级已有受控块时子项目不重复，只加载有 repo 证据的模板。

## Pattern Routes

按任务与 repo 证据匹配 signal；读取后判断 forces，不强制采用。

- 后台 consumer、线程池、subscription / listener、启动/销毁 hook、shutdown、滚动发布、重启或扩缩容 → `patterns/graceful-shutdown-anti-leak.md`
- Consumer 业务动作需按用户 ID 等关键标识独立重试、人工补做或 backfill，或业务动作与消息 handler 耦合 → `patterns/consumer-owned-retryable-execution-unit.md`
- UI 写操作与 polling / SSE / WebSocket / cache revalidation / 并发响应并存，或存在 pending、optimistic、Undo、乱序覆盖 → `patterns/ui-interaction.md`
- 过期 / 状态数据批量删除缺少合适业务索引，代码使用 keyset / cursor / checkpoint，或需要用 `EXPLAIN` 约束扫描放大 → `patterns/primary-key-sweep-for-destructive-cleanup.md`
- 表使用 `is_delete` / `is_deleted` / `deleted_at` 软删除，同时存在业务唯一键、删除后复用、recreate / restore，或 `UNIQUE(business_key, is_delete)` 与 Boolean / BIGINT 语义不明 → `patterns/lifecycle-safe-soft-delete-uniqueness.md`
- 定时 / 批处理 / leader-only 长任务使用固定 TTL 分布式锁，任务可能超过 TTL，或 watchdog、owner-safe renew / release、fencing 语义不明 → `patterns/renewable-owner-checked-lease.md`
- 讨论 ODS / DWD / DIM / DWS / DM / ADS、grain、事实 / 维度、指标口径、CDC、迟到数据、回刷或分层取舍 → `patterns/business-process-first-warehouse-modeling.md`
- Java / JDBC / MySQL 出现 `DATETIME` / `TIMESTAMP`、`Instant` / `LocalDateTime`、connection / session timezone、DST、多时区展示或本地调度 → `patterns/explicit-wall-time-and-instant-boundaries.md`
- 接入或变更外部 API/SDK，HTTP 2xx 混合成功/错误，或 JSON/binary/Content-Type/响应契约不明 → `patterns/vendor-api-contract-preflight.md`
- 缓存模式选型，或 DB / Redis 失效、回填、双删、负缓存、删除复活等分叉窗口 → `patterns/authority-first-cache-consistency.md`；命中后不再加载 `operation-scoped-consistency-contract`
- 分布式状态单选最窄命中，不级联加载：
  - 多区域统一 API、单 authority、forwarding edge、versioned projection / write-through → `patterns/single-writer-forwarding-edge-replica.md`
  - “可写副本 / 多主 / leader proxy”含义不清，需要拆分 ingress、authority、ordering、commit 与 projection → `patterns/authority-ordering-replication-separation.md`
  - 非具体缓存选型的强一致 / 最终一致 / CP / AP / RYW，需要逐操作定义 commit、visibility、partition 与 unknown outcome → `patterns/operation-scoped-consistency-contract.md`
  - 其他跨边界状态设计，正在比较 consensus、atomic commit、Saga、CRDT 或恢复边界 → `patterns/failure-model-first-distributed-state-design.md`

## Safety Gates

- 写入须有明确目标与范围；复用用户已有授权。新增未授权模板、hook 或构建集成时，先展示具体改动再确认。
- 团队 / 外部项目不注入个人路径、私有 helper 或 `preferences/*`。
- 不临场编写模板外 hook。已提供 partial 也要先在目标 repo 验证命令并披露目标与行为；复用已明确的 hook 授权，只有范围未定时才确认。
- pattern/pitfall 晋升按对应 reference 保留可核验 evidence；一次性事故不进长期模板。

## Completion Standard

按选中模板实际验证；注入或 audit 验收由命中的 direct reference 负责。
