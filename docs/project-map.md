# 个人 AI 系统地图

本文件用于判断一个改动应该落在哪个维护边界里。repo 只是维护边界，不等于系统分类。

## 分类规则

- AI 系统模块：约束、增强或编排 AI 怎么工作，例如 `ai-meta`、`larkbot`、
  `rollerskate`；准备封存的历史模块仍保留映射，但不再承接新的 ownership。
- 工作域：管理现实目标、事务、知识或进度，例如 `gtd`。
- 子模块：模块或工作域内部的长期组成部分，例如 `ai-meta / coding-conventions`。
- 任务：一次性修复、迁移、验证或探索，完成后沉淀到对应模块、工作域或子模块。

## 核心模块与工作域

| 名称 | 类型 | 维护边界 | 主要职责 | Context |
| --- | --- | --- | --- | --- |
| `ai-meta` | AI 系统模块 | `<maintenance-checkout>` | `~/.ai/` 配置、共享指令、工具路由、ai-meta 自有 skills、项目 skill 注册、commands、软链发布、context 协议 | `amt` |
| `gtd` | 工作域 | `Projects/gtd` | 目标、任务、待办、日历、项目推进，以及 WorkItem 投影、tracker lifecycle、持久资源和 source closeout | `gtd` |
| `snippet-lab` | 工作域 | `reference/snippet-lab` | 个人可复用 snippets 与示例用户值班周期工单分析 | `snippet-lab` |
| `symphony-lite` | AI 系统模块（待封存） | `Projects/symphony-lite` | 历史 WorkItem 控制核与 Dashboard；冻结新增能力，只保留迁移和封存前的兼容入口，不再拥有 WorkItem lifecycle 或执行自动化 | `sl` |
| `larkbot` | AI 系统模块 | `Projects/larkbot` | 飞书机器人、消息收发、会议助理、prompt、运行时安全边界，以及 canonical `skills/larkbot` agent workflow | `larkbot` |
| `rollerskate` | AI 系统模块 | `Projects/rollerskate` | 由中心 Server 与用户设备上的 Local Runtime 组成的 Agent proactive system；Local 负责 WorkItem 所触发的 Agent Run、Session、workspace authority、执行、恢复与 trace，但不拥有 WorkItem lifecycle | `rs` |

## ai-meta 子模块

| 子模块 | 职责 | 入口 |
| --- | --- | --- |
| `coding-conventions` | 编码规范模板、个人偏好、可复用工程 pattern、模板同步脚本和项目级 `AGENTS.md` 注入规则 | `skills/coding-conventions/SKILL.md`, `skills/coding-conventions/patterns/`, `sync-conventions.sh` |
| `design-direction` | UI 设计方向初始化、现有视觉基线恢复和 specialist design lens 路由 | `skills/design-direction/SKILL.md` |
| `final-form` | 把模糊需求收束为可执行 work order，明确 scope、验收、阻塞问题和分发目标 | `skills/final-form/SKILL.md` |
| `grill` | 对 plan、设计、规则和协作模式做连续追问压测，达成可执行或可放弃的理解 | `skills/grill/SKILL.md` |
| `steelman` | 在取证后、裁决前恢复争议观点的最强可行版本，完成有界挑战、分水岭识别与明确裁决 | `skills/steelman/SKILL.md` |
| `review-router` | 为代码变更选择 simple、challenge、two-axis、quality、prune 或 evolution review；通过显式 `design` strategy 评审方案语义与可实施性 | `skills/review-router/SKILL.md` |
| `loop-ledger` | 从 intent、context、`ff` 编译路径显式绑定的可恢复执行契约，并用验证和人工检查点控制推进 | `skills/loop-ledger/SKILL.md`, `commands/ll.md`, `scripts/verify-ll-contract` |
| `save/load-context` | 跨 session context 保存与加载、恢复索引格式、Codex skill 包装 | `skills/save-context/SKILL.md`, `skills/load-context/SKILL.md` |
| `agent-doc-hygiene` | agent-facing 文档治理、加载路径瘦身、context/memory 有效性巡检 | `skills/agent-doc-hygiene/SKILL.md` |
| `doc-arch-review` | 架构文档、ADR、OKF、doc-root taxonomy 和 durable docs 的质量评审 | `skills/doc-arch-review/SKILL.md` |
| `engineering-exit` | 实现完成后的源码、验证、文档生命周期、浅 gate、release preflight 和 MR 提审收束 | `skills/engineering-exit/SKILL.md` |

## snippet-lab 子模块

| 子模块 | 职责 | 入口 |
| --- | --- | --- |
| `lark-ticket-insights` | 示例用户值班周期的工单分析方法与输出契约 | `reference/snippet-lab/skills/lark-ticket-insights/SKILL.md` |

## rollerskate 子模块

| 子模块 | 状态 | 维护边界 | 职责 |
| --- | --- | --- | --- |
| `server` | 待实施 | `Projects/rollerskate/server` | 中心控制面：用户登录、设备注册、Agent identity 与 Home Runtime placement、离线消息队列和控制状态；不直接持有用户本地 workspace、路径授权或 secrets |
| `local` | 已实施 | `Projects/rollerskate/local` | 每台电脑唯一的 Local Runtime：为多个 Agent 共享一个 eventloop / proactive loop，持有每个 Agent 的 sandbox workspace、本地授权、secrets、执行状态和可离线运行能力；当前 `app`、`event`、`trust`、`runtime`、`handler`、`agent`、`workspace` 七个顶层模块及 Core Chat Handler、Matrix、Codex 链路均归此模块 |

Rollerskate 的部署和身份不变量：一个用户账号可以登录多台电脑；每台电脑运行一个 Local Runtime；每个 Agent 同一时刻只属于一个 Home Runtime，并以 `<workspace>/<name>` 作为默认 cwd。Home Runtime 离线时，Server 暂存消息并把 Agent 标记为 unavailable，不自动故障转移。Agent 换电脑必须显式迁移，并在新设备重新批准额外路径和 secrets。

## 水平客户端归属

| 客户端 / 层 | 维护边界 | 归属说明 |
| --- | --- | --- |
| Claude Code | `~/.claude/CLAUDE.md`, `~/.claude/commands/`, `~/.claude/skills/` | 最后一跳适配层；长期规则和入口源文件仍在对应 owner repo，`~/.ai` 只做聚合 |
| OpenCode | `~/.config/opencode/AGENTS.md`, `~/.config/opencode/commands/`, `~/.config/opencode/skills/` | 最后一跳适配层；通过软链共享全局指令、commands 和 skills |
| Codex | `~/.codex/AGENTS.md`, 可发现 skills / MCP tools | 没有本地 slash command / subagent 目录概念；需要用户可见入口时必须提供 `skills/<name>/SKILL.md` 或 MCP / 脚本桥接，不能只发布 `~/.ai/commands/<name>.md` |
| `~/.ai` 聚合层 | `~/.ai/instructions.md`, `~/.ai/tool-routes.md`, `~/.ai/commands/`, `~/.ai/scripts/` | 本机运行态聚合点，不是长期事实源；能进 git 的内容回到对应 owner repo |
| repo 源文件层 | `<maintenance-checkout>` 与能力 owner repos | 版本管理的 source of truth；ai-meta 维护全局底座、自有 skills 和发布注册，项目能力 skill 留在 owner repo |

ai-meta 可以生成一个放在 `reference` 层并同步到私有 GitHub 的脱敏 `distribution` checkout。它在目标电脑上拥有安装和使用事实，但不建立第二套能力演进 ownership；agent 必须读取根目录 `.ai-meta-repo-role.json`，不得用 basename 或历史绝对路径在 `maintenance` 与 `distribution` 之间猜选。

## 核心职责分工

- `ai-meta` 负责 AI 工具底座：规则、路由、ai-meta 自有技能、项目 skill 注册、安装和跨客户端一致性；项目能力 skill 的 workflow 由对应 owner repo 维护。
- `gtd` 负责现实目标和 WorkItem 控制面：从 source 生成可重建投影，维护 tracker lifecycle、资源、执行 binding、dispatch / reconcile adapter 和 source closeout。
- `rollerskate` 负责 WorkItem 执行面：接收 GTD 固定 revision 的运行请求，拥有 Agent Run、Session、workspace grant / revision、异步 continuation、恢复和 trace；它不读取或推进 WorkItem lifecycle。
- `symphony-lite` 进入封存准备状态：不再新增 WorkItem ownership 或自动化能力，只在迁移完成前保留历史实现和兼容入口。

WorkItem 自动化不建立第三套事实源：GTD 的 `scripts/workitem/` 是控制面 owner，Rollerskate 的 Local Runtime 是执行面 owner；`~/.ai/symphony/` 只是既存运行态路径，名称不表示 `symphony-lite` 继续拥有 WorkItem。Rollerskate 的中心 Server 提供跨设备可达的控制面，但不成为用户本地执行数据的事实源；每台电脑上的 Local Runtime 才持有 workspace、权限、secrets、Event/Runtime state 和停止权，并用同一个 loop 接收可信网络 Command / Response 与本地 Event / Schedule，编排 trigger、capability、attention、Agent 和 plugin。它不接管 `gtd` 的个人任务与 WorkItem lifecycle、`ai-meta` 的跨客户端规则、Matrix 的消息历史或 `larkbot` 的飞书消息事实。当前已实现内容全部归 `rollerskate / local`；入口是 `Projects/rollerskate/docs/architecture/index.md`，未实现部分仍以 `Projects/rollerskate/docs/plan/index.md` 为计划入口。

`context` 不替代这些 source of truth。它只保存恢复索引：当前 route、Doing、Blocked、
Next Steps 和必要锚点；长期事实应回写到对应模块或工作域。

## 接入规则

新增模块、工作域或子模块时，先补齐：

- 名称和类型。
- 维护边界。
- 主要职责。
- context abbr。
- 入口文件。
- 明确不归它管的内容。
