# ai-meta

个人 AI 工具链配置的参考实现。

这个仓库不是一个拿来即用的通用工具包，而是一套个人实践的公开样本：如何让 Claude
Code、OpenCode、Codex 等 AI 编程工具共享长期规则、工程偏好和稳定工具入口，又保留各自
原生的能力边界。

它关注的不是“再收集一批 prompts”，而是让 AI 协作具备可维护、可恢复、可验证的工作流。

## Repository roles

根目录 `.ai-meta-repo-role.json` 区分两种 checkout：`maintenance` 是内部工作源，`distribution` 是经过脱敏、用于其他电脑安装和使用的私有发行副本。发行副本在所在电脑上自包含，不要求存在固定的 `<maintenance-checkout>` 路径；只有明确给出 maintenance checkout 时，才把上游演进切回工作源。

## 项目卖点

### 1. 一个事实源，适配多个 AI 客户端

长期规则、skills、commands、脚本和架构文档都在 repo 中维护；`~/.ai/` 只负责本机聚合，
Claude Code、OpenCode、Codex 的配置目录只做最后一跳适配。

这样可以：

- 在三个客户端之间共享真正稳定的规则和工具入口。
- 明确保留客户端差异，不为了表面一致而维护脆弱的兼容层。
- 让可版本管理的内容回到 repo，让 token、context 和缓存留在本机。

### 2. 从恢复现场到工程退出的完整工作闭环

ai-meta 不只管理启动 prompt，也维护 agent 完成一段工作的完整路径：

```text
加载项目规则与工程约定
  -> load-context 恢复最小现场
  -> final-form / grill 收束目标和关键未决点
  -> loop-ledger 绑定可验证、可恢复的运行契约
  -> task skill 执行、诊断或评审
  -> engineering-exit 收束代码、文档、验证与提审材料
  -> save-context 保存下一次真正需要的恢复索引
```

这些环节按需组合。轻量问题不必跑完整链路；需要持续执行、人工接管、提审或跨 session
恢复时，才进入对应的控制环节。

### 3. 可恢复执行，而不是依赖聊天记录碰运气

`save-context` / `load-context` 保存的是最小恢复索引，而不是会不断膨胀的会话摘要。`loop-ledger` 把目标、范围、完成条件和约束固定在同一文件的前块，普通目标轮只读这一小块；checkpoint、证据、反馈和退出状态以事件追加在后块，只有恢复、人工 gate、状态转换和 final audit 才按需读取。这样同一任务既能被当前 session、WorkItem 或 handoff 明确绑定和续接，又不会让每轮输入随执行历史增长。

这套分层把不同信息送回各自的 source of truth：

```text
项目架构、事实和决策       -> 项目 durable docs
目标、任务和项目进度       -> GTD / Daily Note
可恢复执行现场             -> context
运行控制和验证边界         -> loop-ledger contract
可复用的 agent 改进        -> ai-meta 的规则、skill 或工具入口
```

### 4. 工程偏好可以声明、复用和同步

`coding-conventions` 把个人工程偏好从临场 prompt 变成项目可声明的模板。项目可以按技术栈
选择 `general`、`testing`、`python`、`java-gradle`、`cli`、`frontend`、`git` 等模板，
再通过同步脚本注入 `AGENTS.md` 的受控区域。

它解决的是：让 agent 每次进入项目都读到同一套工程约定，同时不把个人本机路径和私有
习惯硬塞进团队仓库。

### 5. 把高频协作问题做成可发现的能力

仓库中的 skills 不是 prompt 收藏，而是带触发边界、输入输出和安全门的工作流：

- [Context 套件](docs/architecture/context-suite.md)：在输入阶段注入项目与工具路由，结束阶段检查 MR 链接遗漏并有界补正；通过 Codex lifecycle hooks 工作。
- `final-form`（用户调用 `ff`）：把模糊需求整理成可执行、可分发、可验收的 work order。
- `grill`：连续压测 plan、设计或规则，直到关键结构性问题被说清楚。
- `loop-ledger`（用户调用 `ll`）：把已确认工作单编译为准确的 Codex goal 与单文件运行契约，并管理恢复、验证和人工检查点。
- `design-direction`（用户调用 `dd`）：为 UI 工作建立或恢复设计方向，避免迭代过程中风格漂移。
- `review-router`（用户调用 `rr`）：按变更风险选择 simple、challenge、two-axis、quality、prune 或 evolution review；显式 `rr design` 评审方案语义与可实施性。
- `agent-doc-hygiene`：治理 agent 高频加载文档，减少重复、陈旧规则和无效上下文。
- `doc-arch-review`：评审架构文档、ADR、知识分层和 source-of-truth 边界。
- `engineering-exit`：在实现后统一收束源码、文档、验证证据和 MR 准备。

Codex 不发现本地 slash command 目录，因此面向 Codex 的能力会通过可发现 skill、MCP tool、
脚本或 plugin 暴露；支持 slash command 的客户端仍可使用薄 command 入口。

### 6. 用明确边界控制上下文和文档腐化

ai-meta 为不同 artifact 划定职责：

- `README.md` 解释项目价值和可借鉴的设计。
- `AGENTS.md` 保存 agent 执行时必须知道的规则。
- `docs/architecture/` 保存当前有效的架构事实、不变量和变更指导。
- `docs/project-map.md` 登记模块、工作域和子模块的维护归属。
- skills 保存任务特定的长工作流。
- context 只保存 Doing、Blocked、Next Steps 和必要锚点。

同一规则只保留一个 source of truth，其他位置使用短摘要或引用，避免 agent 在多个版本之间
猜测哪一份才有效。

## 仓库与本机的边界

repo 存放可版本管理、可复盘、可迁移的内容：

- `instructions.md`：跨工具共享的长期 agent 指令。
- `tool-routes.md`：任务意图到稳定工具入口的路由表。
- `commands/`、`skills/`、`scripts/`：工作流入口与稳定 helper。
- `docs/`：运行架构和个人 AI 系统地图。
- `.agents/plugins/`、`plugins/`：Codex 本地 plugin marketplace 与 source。
- `runtime/`：由 ai-meta 拥有、挂载到 GTD runtime manager 的本地 periodic job registration source。
- `mcp/config.example.json`：GTD 等独立 MCP client 的去敏配置样例；Codex 使用原生命令注册和授权。`scripts/sync-mcp-config` 仅用于旧配置的手工兼容迁移，具体边界见 [source-of-truth boundaries](docs/architecture/source-of-truth-boundaries.md)。

以下内容只留在本机，不进入 git：

- access token、OAuth refresh token 和私有 MCP 运行配置。
- `~/.ai/contexts/` 下的恢复快照。
- `~/.ai/work-items/` 下的本地 work-item 交换文件。
- `~/.codex` 下的 plugin 安装缓存、启用状态和 hook trust。
- 客户端私有配置、工具缓存和生成态文件。

## 本机发布方式

本仓库通过软链安装发布到 `~/.ai/` 和各客户端配置目录：

```bash
bash install.sh
```

安装脚本可重复执行。它只是当前机器的实现方式；借鉴这套架构时，不需要复用相同路径或脚本。安装时注册的本机任务及其运行边界以 [tool routes](tool-routes.md) 和对应脚本为准。

## 进一步阅读

- [运行架构](docs/architecture/index.md)：水平客户端一致性、垂直 agent workflow、loop
  topology、source-of-truth 边界与 release gates。
- [个人 AI 系统地图](docs/project-map.md)：模块、工作域、子模块和 context abbr 的维护归属。
- [Agent 执行规则](AGENTS.md)：维护本仓库时必须遵守的边界与验证规则。
- [变更历史](changelog.md)：已经完成并沉淀的能力演进。
