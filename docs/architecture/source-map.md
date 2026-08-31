---
type: Reference
title: ai-meta source map
description: ai-meta 的源码归属、生成关系、事实层和验证入口。
resource:
tags: [ai-meta, architecture, source-map]
---

# ai-meta Source Map

## Directory Tree

```text
ai-meta/
├── .ai-meta-repo-role.json # checkout 角色与 source identity
├── skills/                 # 可复用 agent workflow、references 和 templates
├── commands/               # Claude / OpenCode 等客户端的薄入口
├── scripts/                # validator、同步器和本机运维入口
├── release/private/        # 私有发行副本的脱敏 overlay
├── plugins/                # Codex plugin bundle 源文件
├── .agents/plugins/        # personal marketplace 注册源
├── docs/
│   ├── architecture/       # 当前架构、边界和 change guidance
│   └── plan/               # 尚未成为当前事实的项目计划
├── manual/                 # 面向人的工具说明
├── mcp/                    # 共享 MCP 配置结构示例
└── runtime/                # 可版本管理的 runtime registration 示例
```

## Boundary Notes

- `commands/` 不复制 skill 工作流；Codex 可发现性由 skill、MCP tool 或脚本桥接承担。
- `plugins/` 拥有 bundle 源码，`.agents/plugins/marketplace.json` 拥有 marketplace 注册；`~/.codex` 的缓存、启用状态和 trust 是本机运行态。
- `mcp/` 和 `runtime/` 只保存可版本管理的结构；真实 endpoint、token、状态和运行结果位于本机运行态。
- `scripts/private-release` 只允许从 `maintenance` checkout 生成脱敏 `distribution` checkout；发行副本不是第二个维护事实源，也不得反向覆盖工作源。

## Shared Contracts

- `README.md`：面向人的项目入口；不拥有 agent 执行规则或 durable architecture。
- `index.md`：个人项目状态、Next 和 Backlog；不进入公开源码快照时仍是本机项目事实源。
- `instructions.md` 与 `AGENTS.md`：跨客户端全局执行边界和本 repo 维护规则。
- `tool-routes.md`：任务意图到稳定工具入口的事实源。
- `docs/project-map.md`：个人 AI 系统模块、工作域和 context abbr 的归属。
- `~/.ai/agent-frictions.md`：本机可行动摩擦 inbox，不进入 Git；`agent-frictions-archive.md`：已结算历史。
- `changelog.md`：已完成项目历史。
- `route-context.json`：route-context plugin 的可版本管理路由配置。
- `install.sh`：repo source 到 `~/.ai`、`~/.agents/skills` 和各客户端最后一跳的发布关系。
- `.ai-meta-repo-role.json` 与 `scripts/private-release`：checkout source identity、私有发行生成和脱敏校验入口。
- `sync-conventions.sh`：coding-conventions 模板到个人工程入口的受控同步关系。

## Generated And Runtime Mapping

- `~/.ai/` ← repo instructions、commands、skills、scripts 和 config adapter；它是本机 aggregation/runtime 层，不是长期事实源。
- `~/.agents/skills/` ← `skills/` 的 Codex 发现软链。
- 客户端配置目录 ← `install.sh` 发布的最后一跳适配；手工运行态和缓存不得反向成为 repo 事实源。
- `~/.ai/agent-frictions.md`、`~/.ai/frictions/`、`~/.ai/audits/`、`~/.ai/contexts/`、`~/.ai/work-items/`、`~/.ai/loop/` 和含 token 的 MCP 配置是本机私有状态，不进 git。

## Validation

- `python3 -m unittest discover -s scripts -p 'test_*.py'`：scripts、validator、同步器和本机运维入口的主路径回归。
- `scripts/validate-skill <skill-dir>`：上游 skill schema 与 ai-meta invocation / command 集成 gate 的统一入口。
- `scripts/check-codex-command-entries`：发布 command 是否有 Codex 可发现入口。
- `scripts/check-skill-invocation-policies`：skill canonical identity、展示元数据和 explicit-only 策略。
- `scripts/private-release check <distribution-root>`：私有发行副本的本机路径、内网标识、身份信息和凭据形态 gate。
- `python3 plugins/route-context/scripts/test_route_context_resolve.py` 与 `python3 plugins/route-context/scripts/test_route_context_hook.py`：route-context 配置解析和 prompt-time 注入回归。
- `bash install.sh`：发布前预检与本机软链/适配同步。
- `git diff --check`：文档和脚本改动的基础格式检查。

## Architecture Links

- `skills/`、`commands/`、`plugins/`：[Horizontal client consistency](./horizontal-client-consistency.md)。
- `docs/`、`mcp/`、`runtime/`：[Source-of-truth boundaries](./source-of-truth-boundaries.md)。
- 所有主要 root：[Architecture index](./index.md) 与 [Project map](../project-map.md)。

## Change Guidance

- 新增或重命名顶层 source root、发布入口、runtime mapping 或共享 contract 时，同步本文件和对应 architecture shard。
- 普通 skill、script 或文档内部修改不要求机械更新本文件；只有 ownership、生成关系或主要验证入口改变时才更新。
- AGENTS 只链接本文件，不复制本页目录和职责说明。
