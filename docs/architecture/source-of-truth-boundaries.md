---
type: Reference
title: Source-of-truth boundaries
description: Repo, runtime, context, MCP, and install boundaries for ai-meta.
resource:
tags: [ai-meta, architecture, source-of-truth]
---

# Source-of-Truth Boundaries

## Scope

本文件记录 ai-meta 中 repo 源文件、`~/.ai` 聚合层、本机运行态、context、MCP 和 install 脚本的 source-of-truth 边界。

## Current Facts

### Repo And Runtime

- 可版本管理源文件留在各自 owner repo；`<maintenance-checkout>/` 拥有全局底座、ai-meta 自有 workflow 和跨客户端发布注册。
- `~/.ai/` 是本机运行态 aggregation 点，不是长期事实源。
- 能进 git 的内容应该回到对应 owner repo 维护；项目能力 skill 不复制进 ai-meta。
- `~/.ai/contexts/`、`~/.ai/work-items/` 和 token 类本机私有状态不进 git。
- Codex plugin 的 marketplace 描述、manifest、hook adapter 和 helper 脚本进 repo；
  `~/.codex` 里的 marketplace 注册、安装缓存、启用状态和 hook trust 是本机运行态。

### Context Protocol

context 文件位于 `~/.ai/contexts/<abbr>.md`，采用 v2 单文件格式：

- YAML frontmatter 从第一行 `---` 开始，确保通用 Markdown renderer 正确识别。
- frontmatter 第二行短索引注释：project、mainline 状态、workstream 状态、推荐 next route。
- YAML 字段：goal、mainline、workstreams、next_route、updated 等结构化状态。
- Markdown body：Constraints & Preferences、Doing、Blocked、Key Decisions、Next Steps、Critical Context、Relevant Files。

context 只保存恢复索引，不保存完整过程分析；长期事实应回写到 `ai-meta`、`gtd`、
`symphony-lite` 或具体项目自己的 source of truth。

### MCP Boundary

- `~/.ai/mcp/config.json` 保存使用共享配置的独立 MCP client 所需 endpoint、headers 和 OAuth refresh 信息。
- repo 只保留 `mcp/config.example.json`，用于说明结构，不包含 token。
- 各客户端原生注册和认证状态由该客户端拥有；共享配置不覆盖原生 OAuth，也不把客户端私有状态作为跨工具事实源。
- Codex MCP server 由 Codex 原生命令注册和授权；`install.sh` 不复制 MCP 配置或凭据。`scripts/sync-mcp-config` 仅保留为旧共享配置中兼容 remote server 的手工迁移工具，并明确排除使用 Codex 原生 OAuth 的 Meego。

### Install Boundary

`install.sh` 是本机发布脚本，负责软链、旧软链清理和本机配置适配：

- 发布前运行 ai-meta 专用入口预检，确保会发布的 command 有 Codex 可发现 skill / 桥接或显式例外。
- 发布核心文件到 `~/.ai/`。
- 发布 command、ai-meta 自有 skill、已登记 owner-repo skill、hook 和选定 helper。
- 不复制共享 MCP 私有配置或 token 到客户端；各 MCP client 独立注册 server 并持有自己的认证状态。
- 发布客户端最后一跳软链。
- 清理 install script 中仍显式登记的退役入口。

项目 skill source 不存在时，安装器清理自己管理的旧发现软链并跳过该能力；source 存在但缺少 Codex metadata 时失败，避免发布半个 skill。它不负责生成私有 token 配置，也不把运行态 context / work-items 写入 git。

### Project Source Map

- 每个受管源码项目维护独立的 `docs/architecture/source-map.md`，记录稳定 source roots、ownership、共享 contract、生成关系和验证入口。
- 架构入口必须链接 source map；AGENTS 只保留发现指针，不复制正文。
- 内容与 review 分工以 [Project Source Map Contract](./source-map-contract.md) 为准。

## Relationships

- [Architecture index](./index.md)
- [Horizontal client consistency](./horizontal-client-consistency.md)
- [Vertical agent ll](./vertical-agent-ll.md)
- [Project source map contract](./source-map-contract.md)
- [ai-meta source map](./source-map.md)

## Decisions / Invariants

- 源文件进 repo，运行态留本机，客户端目录保持薄软链。
- 新增长期规则时，必须能归属到全局指令、工具路由、skill、script、项目文档或运行态
  context 之一。
- 新增工具入口时，优先沉淀成薄入口，具体流程进入 skill、script 或 durable docs。
- README 面向人说明参考价值，AGENTS.md 面向 agent 说明执行边界。
- 每个项目只有一份 canonical source map；AGENTS 负责发现，架构文档负责事实。

## Change Guidance

改 source-of-truth 边界时，先检查：

- 是否引入新的本机私有状态；如有，默认不进 git，并说明运行态位置。
- 是否让 `~/.ai` 或客户端目录承载了本应进入 repo 的长期事实。
- 是否把 context 变成了过程记录或 durable docs 副本。
- 是否需要同步更新 `install.sh`、`mcp/config.example.json`、Codex plugin marketplace / manifest
  或客户端软链说明。
