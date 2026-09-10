---
type: Reference
title: ai-meta architecture index
description: Entry point for horizontal client consistency, vertical agent workflow, and loop topology.
resource:
tags: [ai-meta, architecture, index]
---

# ai-meta Architecture

## Scope

`ai-meta` 是个人 AI 工具链底座，维护两条正交架构维度：

- 水平维度：让 Claude Code、OpenCode、Codex 在各自能力边界内共享长期规则、稳定工具入口和本机运行态桥接。
- 垂直维度：让 agent 从启动加载、上下文恢复、任务收束、工程收尾到上下文保存形成可自动化的工作流闭环，并明确 turn-based、goal、time 与 proactive loop 的组合边界。

本目录只记录当前有效架构事实、边界、不变量和变更指导。具体项目 / 工作域归属见
[project-map](../project-map.md)；执行规则见 repo [AGENTS.md](../../AGENTS.md)、全局
[instructions.md](../../instructions.md)、各 skill 和 [tool-routes.md](../../tool-routes.md)。

## Current Facts

ai-meta architecture 分为这些稳定 scope：

- [Horizontal Client Consistency](./horizontal-client-consistency.md)：三端一致性、源文件层、`~/.ai` 聚合层和客户端最后一跳适配。
- [vertical-agent-ll](./vertical-agent-ll.md)：启动加载、工程约定注入、context 恢复、`final-form`、主 skill、`engineering-exit`、`save-context` 的闭环。
- [Agent Loop Topology](./agent-loop-topology.md)：turn-based、goal、time 与 proactive loop 的分层、组合、ownership 和成熟度边界。
- [Agent Friction Observability](./agent-friction-observability.md)：Codex 客观事件采集、context / LL ownership、`save-context` 结算和 retention 边界。
- [Context Suite](./context-suite.md)：route-context 输入注入、MR 链接 Stop 检查与插件加载验收。
- [Skill Verification Trace](./skill-verification.md)：skill 改动的 revision identity、静态检查、客户端加载回执、行为样本和 verdict 状态机。
- [Source-of-Truth Boundaries](./source-of-truth-boundaries.md)：repo、`~/.ai`、context、MCP、install 脚本和私有运行态边界。
- [Project Source Map Contract](./source-map-contract.md)：每个项目独立 source map 的内容、准确性、review ownership 和变更触发条件。
- [ai-meta Source Map](./source-map.md)：本 repo 的 source roots、共享 contract、生成关系和验证入口。
- [Gates and Release Preflight](./gates-and-release-preflight.md)：浅 skill gate、`gitlab.flow` 和 release preflight。

这些 shard 是同一个 architecture bundle 的组成部分；不要在单个入口文件重新复制它们的细节。

## Relationships

- [Project map](../project-map.md): 模块、工作域、子模块和水平客户端归属。
- [Changelog](../../changelog.md): 已完成历史。
- [Repo agent rules](../../AGENTS.md): 当前 repo 的 agent 执行规则。
- [Global instructions](../../instructions.md): 全局 agent 指令。
- [Tool routes](../../tool-routes.md): 任务意图到稳定工具入口的路由。

## Decisions / Invariants

- 源文件进 repo，运行态留本机，客户端目录保持薄软链。
- `~/.ai/` 是 aggregation 点，不是长期事实源。能进 git 的内容应该回到对应 owner repo 维护；全局底座和 ai-meta 自有 workflow 回到 `<maintenance-checkout>/`。
- context 只承担恢复索引职责；长期事实回写到对应 source of truth。
- skill 链条保持浅：主 skill + 最多一层 reference；命中明确 gate 才路由 specialist。
- README 面向人说明参考价值，AGENTS.md 面向 agent 说明执行边界。

## Change Guidance

改 architecture bundle 时：

- 新事实先归到一个稳定 shard；只有 bundle 级导航、不变量和关系才写入本 index。
- 如果一个主题有独立维护节奏、独立 source-of-truth 边界、独立 change guidance，或未来自动化会引用它，应拆成独立 shard。
- 不要留下 `docs/architecture.md` 作为第二个架构事实源；附近文档应链接到本 index 或具体 shard。

## History

- 已完成历史见 [changelog](../../changelog.md)。
