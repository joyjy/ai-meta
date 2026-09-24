---
type: Reference
title: Horizontal client consistency
description: Source, aggregation, and client adapter layers for Claude Code, OpenCode, Codex, Kimi Code, and Pi.
resource:
tags: [ai-meta, architecture, clients]
---

# Horizontal Client Consistency

## Scope

本文件记录 ai-meta 的水平维度：Claude Code、OpenCode、Codex、Kimi Code、Pi 如何在各自能力边界内共享规则、入口和本机运行态桥接。

## Current Facts

ai-meta 的水平维度是三层适配：

```text
owner repositories  可版本管理的源文件层
<maintenance-checkout>/   全局底座、ai-meta 自有 workflow 与发布注册
~/.ai/              本机运行态聚合层
工具配置目录         Claude Code / OpenCode / Codex / Kimi Code / Pi 的最后一跳适配层
```

原则：源文件进 repo，运行态留本机，客户端目录保持薄软链。

源文件层：

```text
instructions.md         全局 agent 指令
tool-routes.md          任务意图到稳定工具入口的路由
.agents/plugins/        Codex 本地 plugin marketplace 描述
plugins/*/.codex-plugin/ Codex plugin manifest
commands/               slash command 薄入口
plugins/                Codex 本地 plugin 独立 source 目录
mcp/                    去敏 MCP 配置模板
scripts/                共享 helper
skills/                 ai-meta 自有 skills 和模板；项目能力 skill 留在 owner repo
docs/                   当前目标、运行架构、系统地图
install.sh              发布软链到本机运行态
```

`~/.ai/` 聚合层：

```text
~/.ai/instructions.md    -> <maintenance-checkout>/instructions.md
~/.ai/tool-routes.md     -> <maintenance-checkout>/tool-routes.md
~/.ai/agent-frictions.md 本机可复现工具摩擦和改善队列，不进 Git
~/.ai/commands/          -> <maintenance-checkout>/commands/*.md
~/.ai/scripts/           -> <maintenance-checkout>/scripts/ 中稳定发布的 helper
~/.ai/mcp/config.json    本机私有 MCP 运行态配置，不进 git
~/.ai/contexts/          本机 context 恢复索引，不进 git
~/.ai/work-items/        本机 WorkItem 交换区，不进 git
```

客户端适配层：

```text
~/.config/opencode/AGENTS.md  -> ~/.ai/instructions.md
~/.claude/CLAUDE.md           -> ~/.ai/instructions.md
~/.codex/AGENTS.md            -> ~/.ai/instructions.md
~/.agents/AGENTS.md           -> ~/.ai/instructions.md  # Kimi Code 全局规则
~/.pi/agent/AGENTS.md         -> ~/.ai/instructions.md
~/.pi/agent/skills/           -> ~/.agents/skills/

~/.config/opencode/commands/  -> ~/.ai/commands/
~/.claude/commands/           -> ~/.ai/commands/

~/.config/opencode/skills/    -> ~/.ai/skills/
~/.claude/skills/             -> ~/.ai/skills/
~/.agents/skills/             -> <maintenance-checkout>/skills/ + registered owner-repo skills
~/.codex/plugins/cache/       Codex plugin 安装缓存，本机运行态
```

Codex 没有本地 slash command / subagent 目录概念，因此共享全局指令，并通过可发现
skills、MCP tools、单一脚本入口或 Codex plugin lifecycle hooks 桥接能力。repo 可维护本地
plugin marketplace 和独立 plugin 目录；`~/.codex` 中的安装缓存、启用状态和 hook trust 属于
本机运行态。各客户端目录和入口细节的维护归属见 [project-map](../project-map.md)。

项目能力 skill 由能力 owner repo 维护 canonical 包，ai-meta `install.sh` 只登记其 source root，并将同一目录软链到 `~/.ai/skills/` 与 `~/.agents/skills/`。owner repo 不存在时跳过该能力并清理 ai-meta 管理的旧软链，不在 ai-meta 复制 fallback 内容。

显式调用策略属于客户端适配元数据。仅允许用户主动运行的 skill 在共享 `SKILL.md` frontmatter 中声明 `disable-model-invocation: true`，供 Claude 读取；如果 Claude 同时发布 command 薄入口，该 command 也声明相同字段。Codex 在 skill 目录的 `agents/openai.yaml` 中声明 `policy.allow_implicit_invocation: false`。`engineering-exit`、`load-context`、`loop-ledger` 和 `save-context` 始终仅显式调用；`agent-assignment` 在维护版自动路由，在发行版由用户显式调用。`agent-doc-hygiene`、`grill`、`review-router` 和 `steelman` 保留语义触发及 agent 主动路由能力。缩写只存在于用户 command / invocation，不作为第二个 skill identity。

## Relationships

- [Architecture index](./index.md)
- [Project map](../project-map.md)
- [Source-of-truth boundaries](./source-of-truth-boundaries.md)

## Decisions / Invariants

- 一致性是能力边界对齐，不是把所有客户端强行做成同一种入口。
- 命令文件只做薄入口，具体流程进入 skill、script 或 durable docs。
- 客户端目录只做最后一跳适配，不成为跨工具事实源。
- 显式调用策略必须在 Claude 和 Codex 的元数据层同时表达，并由 `scripts/check-skill-invocation-policies` 在安装前校验。

## Change Guidance

改水平维度时，先检查：

- 是否改变 `<maintenance-checkout>/`、`~/.ai/`、客户端适配目录之间的 source-of-truth 边界。
- 是否需要更新 `install.sh`、`tool-routes.md`、[project-map](../project-map.md)、Codex plugin
  marketplace / manifest 或客户端软链说明。
- 是否引入新的本机私有状态；如有，默认不进 git，并说明运行态位置。
