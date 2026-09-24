---
type: Reference
title: vertical-agent-ll
description: The recoverable agent workflow from startup loading through context saving.
resource:
tags: [ai-meta, architecture, agent-ll]
---

# vertical-agent-ll

## Scope

本文件记录 ai-meta 的垂直维度：agent 从启动加载、工程约定注入、上下文恢复、任务收束、工程收尾到上下文保存的稳定 ll。自动化应依赖这个 ll 的稳定输入输出，而不是读取会话历史。

## Current Facts

ai-meta 当前维护的 agent workflow loop：

```text
AGENTS.md / CLAUDE.md load order
  -> coding-conventions 注入工程执行偏好
load-context
  -> final-form
  -> ll contract gate when controlled execution or recovery is needed
  -> 当前任务主 skill
  -> agent-assignment 执行分流（维护版默认；发行版显式调用）
  -> 实现、诊断或评审
  -> engineering-exit
  -> save-context
```

环节职责：

- `coding-conventions` 在项目入口加载阶段注入代码、测试、Git 和验证等工程执行偏好；
  `gitlab.flow` 仍由项目 `index.md`、context / exit skills 与 tool routes 持有，它不写入恢复 context。
- `load-context` 只恢复当前项目 / 分线的最小上下文和健康信号。
- `final-form` 把模糊需求收束成 sparse work order；默认只保留 Goal、Scope、Acceptance，其他字段按 gate 出现。
- `loop-ledger` 从显式用户请求或已确认 final-form 编译单个 session 文件。显式 `/ll <task>`、`/loop <task>` 或携带任务的 `loop-ledger` skill invocation 本身就是 dispatch authorization；若无结构性阻塞，agent 在同一轮内部编译 sparse final-form 并直接启动，不展示第二次确认。文件前 8 行保留初始化 hot，随后嵌入 `ll.contract.v0`，尾部追加 checkpoint、evidence、feedback、focus、结构化 reply 和 exit 事件。普通 turn 通过 `ll-hot-block` 读取事件投影后的当前 8 行 Focus，并用通用 `ll-turn` 编译结构化结果和下一 Focus；`ll-workitem` 只负责把 WorkItem final-form 初始化为同一种 loop-ledger 文件。恢复、人工 gate、状态迁移和最终审计才由 agent 读取完整文件和相关尾部事件。Codex goal adapter 从 verified exact path 生成准确 objective；Symphony 复用同一 contract/ledger 语义管理 WorkItem session，不改变 `/ll` 的交互行为。
- `loop-ledger` 普通启动和普通 turn 只加载薄主 skill 并调用确定性 helper；架构文档只在修改 `ll.contract.v0`、compiler、verifier、session format 或 adapter 时读取，`runtime-control` 只处理 fast path 被拒、恢复、人工 / 安全 gate 和非普通状态迁移，checkpoint、feedback、terminal audit 与 archive 只在收尾时加载 `closeout` reference。
- 当前任务主 skill 负责本轮实际执行，例如 `coding-conventions`、`agent-doc-hygiene`、
  `doc-arch-review` 或项目外部 skill。
- `agent-assignment` 在维护版的非简单任务首次实质工具调用前选择 direct、RS 或 explicit-model internal；发行版仅在用户显式调用时执行该分流。
- `engineering-exit` 是实现后的总装线，收束源码、验证、文档生命周期、浅 gate、release
  preflight 和 MR 材料。
- `save-context` 保存恢复索引和必要锚点，并在会话证据仍可用时结算当前 scope 的 objective
  friction candidates；长期事实仍回写到对应 source of truth。
- objective friction collector 从 Codex rollout 的结构化 metadata 生成安全候选；
  `save-context` 将 exact events 归属 active loop-ledger 或 context route，并显式 settle；loop-ledger 可按 route
  claim。Codex save 与 loop-ledger closeout 复用同一个 `agent.audit.v1` contract，补充语义 fallback 候选
  和 prompt → final-form → loop-ledger → execution 的 fidelity gap；engineering-exit 只 hand off exact ledger，save-context 作为单一自动 owner 通过 Rollerskate 异步投递给
  `@kimi`，当前主线程不等待，后续 save / follow-up 收取指定结果文件；未执行 save 时才由显式 audit follow-up 补位。Rollerskate 将该隔离 workspace 的 write grant 映射为 Kimi 非交互可写 profile；audit 缺席或 pending 不阻塞 engineering-exit，receipt 绑定的 exact ledger 只在后续 settlement 后归档；主 agent 负责最终结算和 durable output。
  loop-ledger feedback 只控制当前任务修正，旧的 future-loop gap 类型仅兼容读取；自动事件、audit
  report 与 loop-ledger current-task feedback 保持不同 schema 和存储边界。

闭环不要求每轮都跑完全部环节。纯探索、评审、轻量诊断或单命令任务可以停在对应阶段；
需要保存、交接、提审或恢复时再进入后续环节。

## Relationships

- [Architecture index](./index.md)
- [Agent loop topology](./agent-loop-topology.md)
- [Gates and release preflight](./gates-and-release-preflight.md)
- [Source-of-truth boundaries](./source-of-truth-boundaries.md)

## Decisions / Invariants

- `coding-conventions` 注入工程执行偏好，不写入恢复 context。
- `agent-assignment` 是执行分流 source of truth，不由 `coding-conventions` 的偏好目录加载或持有。
- context 只保存恢复索引；durable facts 必须回写到对应 source of truth。
- `final-form` 是模糊需求与可执行任务之间的 sparse 中间层；空 optional groups 不进入默认输出。
- `ll.contract.v0` 仍是运行控制契约；固定控制字段从 base contract 模板复用。新 run 将它嵌入一个 `ll.segmented.v1` session 文件，前块固定、后部只追加，不再为 brief、state 和 evidence 建立多份 loop-ledger 文件。
- Hook 只负责无副作用的确定性上下文装配；goal、WorkItem 或 task dispatch 属于 loop-ledger contract
  验证后的 runtime adapter，不得在 pre-prompt hook 中提前执行。
- objective friction event 的 owner 只能是 exact loop-ledger contract、stable context route 或
  unclaimed；不通过“最新文件”推断 active owner，也不把 event body 复制进 context。
- 单文件 loop-ledger 的普通轮次只读 `ll-hot-block` 输出的 8 行事件投影；agent 直接读取完整 contract 或 ledger tail 必须命中恢复、gate、状态迁移或最终审计。
- 多轮工作细分是 loop-ledger core：同时只有一个 Active Focus，agent 只能提议 `next_focus`，`ll-turn` 校验并追加状态事件；子 Focus 完成不等于 Root 完成，子队列耗尽后必须回到 Root 对照验收。
- 热读块不得按字符静默截断 Goal、Scope、Done 或 Guardrails。contract 编译器为新 run 绑定 `runtime_binding.hot_packet` / `ll-turn@1`，在写入前确定性归一化空白、移除 scope / acceptance 精确重复项，并对包含字段名和固定控制文本的完整 8 行 packet 使用 1200 字符软目标与 1800 字符硬上限；各字段共享总预算，报告总长和逐字段贡献，仍超出硬上限时初始化失败，不得丢失要求。既有 `800/1200` contract 保持可读并继续执行其内嵌旧预算；没有 packet policy 的 contract 也保持可读，但不宣称满足预算。普通 packet 只携带协议版本和 goal 已绑定的 exact path 语义，不重复完整 reply schema、命令或绝对路径。
- 当前 loop-ledger runtime 支持从显式用户请求或已确认 final-form 创建 Codex goal；前者不得被 final-form 的普通展示确认边界重复拦截。其他 adapter 值仅保留 legacy contract 验证兼容，不代表可 dispatch。
- `engineering-exit` 编排浅 gate，但不递归执行 broad specialist workflow。

## Change Guidance

改垂直 ll 时，先检查：

- 新规则属于 ll 的哪个环节：加载、工程约定注入、context 恢复、`final-form` 收束、主 skill、执行分流、
  `engineering-exit`、`save-context`，还是 specialist gate。
- 是否会拉长 skill 链条；如果需要第二层以上 specialist，优先改成 follow-up work order。
- 是否把 durable facts 误写进 context，或把执行记录误写进 architecture docs。
- 是否影响自动化；自动化应依赖 `ff` 和 `ll.contract.v0` 的稳定输入输出，而不是会话历史。
