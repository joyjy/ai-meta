# ai-meta

本仓库负责维护 `~/.ai/` 工具链配置，让 Claude Code、OpenCode、Codex 在各自能力边界内
共享长期规则和稳定工具入口。这里的一致性是能力边界对齐，不是把所有客户端强行做成同
一种入口。

## Repository Role

- 先读根目录 `.ai-meta-repo-role.json`。`maintenance` checkout 拥有能力演进和发布生成；`distribution` checkout 是当前机器安装、使用和本地诊断的事实源，但上游维护必须由用户或项目 route 提供 exact maintenance root。
- 不得按仓库名、相邻目录或历史路径猜测另一个 checkout。`distribution` 中没有 exact maintenance root 时留在当前 checkout；若请求明确涉及上游发布演进则停在 source-identity checkpoint。

## 维护边界

- 当前目标、纳管范围、软链拓扑和 MCP 边界以 [`docs/architecture/index.md`](docs/architecture/index.md)
  为 source of truth；本文件只保留 agent 执行时必须知道的规则。
- 本 repo 的源码归属、生成关系和验证入口以 [`docs/architecture/source-map.md`](docs/architecture/source-map.md) 为 source of truth。
- 个人 AI 系统模块、工作域、子模块和 context abbr 的归属以
  [`docs/project-map.md`](docs/project-map.md) 为准；新增长期对象时先登记维护边界。
- ai-meta 自有源文件在本 repo；项目能力的 canonical skill 留在 owner repo，由 `install.sh` 登记并发布发现软链。`~/.ai/` 只放软链或本机运行态文件；各工具配置目录只做最后一跳适配。
- `~/.ai/contexts/`、`~/.ai/work-items/` 和含 token 的 `~/.ai/mcp/config.json` 不进 git。
- 允许经由 `~/.ai/instructions.md` 编辑全局指令，但该路径必须保持为指向 `instructions.md`
  的软链；若被编辑器替换成真实文件，运行 `bash install.sh` 修复。

## 编辑规则

- 本仓库入口文档保持薄：README 写给人，AGENTS.md 写给 agent，架构和范围写
  `docs/architecture/index.md` 及其 shards，系统地图写 `docs/project-map.md`。
- 文档正文默认使用中文；`architecture`、`design`、`context` 等英文只在文件名、路径、
  schema / API / CLI 术语或既有专名中保留，解释性句子不要顺手写成英文。
- agent 生成的执行计划、迁移计划、分阶段落地方案等未实现文档，默认放到项目层
  `docs/plan/`；只有已经实现、验证并沉淀为当前有效事实的内容，才进入源码 repo 的
  `docs/` 架构、ADR、runbook 或 change guidance。
- 命令文件只做薄入口，具体流程收敛到对应 skill、script 或 durable docs。
- 新增、重命名或实质修改会发布的 `commands/*.md` 时，必须让 `scripts/check-codex-command-entries`
  通过；`install.sh` 发布前会执行该检查。不要只因为 `~/.ai/commands/<name>.md` 软链存在就认为
  Codex 可用。
- 仅允许用户显式调用的 skill 必须同时维护 Claude 的 `disable-model-invocation: true` 和 Codex 的 `agents/openai.yaml` → `policy.allow_implicit_invocation: false`；若 Claude 还发布同名 command，command frontmatter 也必须声明前者。修改后运行 `scripts/check-skill-invocation-policies`。
- 每个发布给 Codex 的 skill 都必须在 `agents/openai.yaml` 维护 `interface.display_name` 和 `interface.short_description`；是否允许隐式调用仍由独立的 `policy.allow_implicit_invocation` 决定。
- 发布 skill 的 canonical identity 必须是描述性 kebab-case，且 `skills/<id>/`、frontmatter `name`、首个 H1 和 `agents/openai.yaml` 的 `display_name` 完全一致；不另建 Title Case 展示名。`cc`、`dd`、`ee`、`ff`、`ll`、`rr` 等缩写只作为用户调用 alias 或 command 入口，不进入 canonical path、标题或普通 agent 文案。
- `~/.ai/agent-frictions.md` 是本机跨项目工具摩擦 inbox；维护时按 `tool-routes.md` 的「Agent 执行摩擦」入口读取，纯恢复按 `load-context` 的 count-only 规则执行；详情仅在修复或 triage 时展开。
- 维护跨客户端入口前先确认目标客户端发现机制。Codex 没有本地自定义 agents / slash commands 目录概念；需要桥接工作域能力时，使用可发现 skill、MCP tool 或脚本入口，不能只落 `commands/*.md` / `~/.ai/commands/*.md`，也不机械套用 Claude / OpenCode 的 subagent 结构。
- 个人 l3 项目的测试优先覆盖主路径 smoke / integration；确认 CLI / command 调用的接口和
  参数正确、关键接口能跑通即可。默认不为边界排列、格式细节、help 文案或内部 helper 铺大量
  单测，除非它曾真实导致事故或会造成写操作风险。
- loop-ledger Python 测试从 repo root 运行 `python3 -m unittest discover -s scripts -p 'test_ll*.py'`；不要把 `scripts/test_*.py` 文件路径直接传给 `python -m unittest`。
- 验证投入默认收缩：只保留有独立 oracle 的结构校验、不可逆 / 高风险写操作前的 smoke、
  以及真实事故回归。不要为了证明 agent 理解 skill 文案而写测试；不要为 ignored workpad /
  plan、探索性计划、help 文案、格式细节或模型生成实现后的同构测试投入工程化验证。
- 测试文件减法门槛：凡修改 `test/*.mjs`，必须先检查同文件是否有低价值 help 文案断言、
  过时入口断言、重复 fixture 或非主路径边界断言；能删则删或合并。若本次没有删除任何测试
  代码，最终说明必须写明“未删减原因”。

## coding-conventions 适用范围

- 本仓库以 skill、command 和文档入口为主，不常驻接入 `coding-conventions:begin general` 受控块。
- 修改 `scripts/`、测试、安装脚本或其他工程代码时，可按需读取 `general` 模板作为本次
  session 的工程偏好，但不要让它覆盖 skill / command / durable docs 的维护规则。
