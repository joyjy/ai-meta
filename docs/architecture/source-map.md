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
├── plugins/                # plugin bundle 源文件；Claude Code 直接引用其中的 hook 脚本
├── .agents/plugins/        # Codex personal marketplace 注册源
├── docs/
│   ├── architecture/       # 当前架构、边界和 change guidance
│   ├── reference/         # 跨场景共享判断规则
│   ├── runbook/            # 工具路由按需引用的操作流程
│   └── plan/               # 本机项目计划，Git 忽略；源码快照中可能不存在
├── manual/                 # 面向人的工具说明
├── mcp/                    # 共享 MCP 配置结构示例
└── runtime/                # 可版本管理的 runtime registration 示例
```

## Boundary Notes

- `commands/` 不复制 skill 工作流；ai-meta 自有 workflow 留在 `skills/`，项目能力的 canonical skill 留在 owner repo。Codex 可发现性由 skill、MCP tool 或脚本桥接承担。
- `plugins/` 拥有 bundle 源码，`.agents/plugins/marketplace.json` 拥有 Codex 的 marketplace 注册；`~/.codex` 中的缓存、启用状态和 trust，以及 `~/.claude/settings.json` 中指向本 checkout 的 hook 引用，是本机运行态。
- `mcp/` 和 `runtime/` 只保存可版本管理的结构；真实 endpoint、token、状态和运行结果位于本机运行态。
- `scripts/private-release` 只允许从 `maintenance` checkout 生成脱敏 `distribution` checkout。发行副本不是第二个维护事实源。禁止发行副本反向覆盖工作源。

## Shared Contracts

- `README.md`：面向人的项目入口；不拥有 agent 执行规则或 durable architecture。
- `index.md`：个人项目状态、Next 和 Backlog；不进入公开源码快照时仍是本机项目事实源。
- `instructions.md` 与 `AGENTS.md`：跨客户端全局执行边界和本 repo 维护规则。
- `tool-routes.md`：任务意图到稳定工具入口的事实源。
- `docs/project-map.md`：个人 AI 系统模块、工作域和 context abbr 的归属。
- `~/.ai/agent-frictions.md`：本机可行动摩擦 inbox，不进入 Git；`agent-frictions-archive.md`：已结算历史。
- `scripts/skill_verification.py`：skill 改动验证账本的 schema、fingerprint、过期检测、事件写入和 verdict 计算；`scripts/skill-verification` 是薄入口。
- `scripts/daily_review_collect.py`：`skills/daily-review` 的确定性事实包。内容包括 5 类：Codex 与 Claude Code 会话及逐轮模型与强度、自动化配置、待结算 receipt、open 验证记录、收尾必做事项缺口。`scripts/daily-review-collect` 是薄入口。Codex 定时任务 `~/.codex/automations/automation/automation.toml` 只保留指向该 skill 的入口。
- `scripts/rule_eval.py`：用冻结场景盲测规则文本或模型配置的新旧版本，经 Rollerskate DAG Run 执行并按预定答案判定；spec 格式与判定规则见 [rule-eval runbook](../runbook/rule-eval.md)，`scripts/rule-eval` 是薄入口。
- `scripts/claude_session_title.py`：save-context 在 Claude Code 中写入当前会话标题（追加客户端 `custom-title` 记录，属内部格式）；`scripts/claude-session-title` 是薄入口。其中按 `CLAUDE_CODE_SESSION_ID` 定位会话日志的函数也供 `save_context_timeline.py` 复用。
- `scripts/save_context_timeline.py`：save-context timeline 时间段的确定性来源，读取 Codex rollout 或 Claude Code 会话日志中的用户消息时间；`--from/--to` 输出日期范围内全部用户会话的消息时间点、cwd 与 load-context / save-context 路由证据（`save-context-timeline.sessions.v1`），供 GTD 工时推断消费，本脚本不做时长推断；`scripts/save-context-timeline` 是薄入口。
- `scripts/load_context.py`：load-context 的只读 route 投影（`load-context.projection.v1`），解析 context.v3 并检查选中段落中临时路径是否存在；省略 route 时通过 `gtd project resolve` 绑定项目；`scripts/load-context` 是薄入口。
- `scripts/cli_usage.py`：ai-meta 自有 CLI 共用的本地 usage 记录与汇总，日志位于 `~/.ai/usage/`。
- `scripts/amt-git-refresh`：仓库刷新、分支扫描和按快照确认清理。`scripts/amt_branch_review.py` 持有内容证据、分类与报告投影；定时任务保持 dry-run，执行契约见 [runbook](../runbook/git-branch-cleanup.md)。
- `scripts/wt_sweep.py`：worktree 盘点判定（`wt-sweep.list.v1`）与核验后删除，判定语义由 `skills/coding-conventions/references/worktree-lifecycle.md` 持有；`scripts/wt-sweep` 是薄入口。
- `scripts/docker_test_sweep.py`：Docker 测试产物盘点判定（`docker-test-sweep.list.v1`）、核验后删除与 prune 报告（`docker-test-sweep.prune.v1`），判定语义由 `tool-routes.md`「Docker 测试产物清理」持有；`scripts/docker-test-sweep` 是薄入口。
- `scripts/save_context_audit_rs.py`：save-context 审计的派发、回读、结算与清理编排；`save_context_audit_archive.py` 拥有归档白名单、打包、完整性校验及 Run 归档状态查询，`save_context_audit_io.py` 提供两者共用的进程调用、JSON 解析和原子写入。
- `changelog.md`：已完成项目历史。
- `route-context.json`：context 套件输入侧的可版本管理路由配置；`plugins/route-context/` 保留既存插件身份，包装输入路由和普通任务行动承诺 Stop 检查；Claude Code 不安装插件，由 `~/.claude/settings.json` 直接运行其中的 `hooks/route-context-user-prompt.js`。
- `scripts/claude-statusline`：Claude Code status line 渲染；`~/.claude/settings.json` 只保存指向 `~/.ai/scripts/claude-statusline` 的本机引用。
- `plugins/route-context/hooks/codex-response-style.js` 与同目录规则正文、配置模板：Codex 用户级模型表达 hook；精确匹配 `gpt-6.1-sol`，安装与真实验收见 [runbook](../runbook/codex-response-style.md)。
- `scripts/claude-notify`：Claude Code Notification hook 适配，把 `idle_prompt` / `permission_prompt` 转为 `larkbot notify send`；投递由 larkbot 负责，`~/.claude/settings.json` 只保存指向 `~/.ai/scripts/claude-notify` 的本机引用。
- `install.sh`：ai-meta source 与已登记 owner-repo skill 到 `~/.ai`、`~/.agents/skills` 和各客户端最后一跳的发布关系。
- `.ai-meta-repo-role.json` 与 `scripts/private-release`：checkout source identity、私有发行生成和脱敏校验入口。
- `sync-conventions.sh`：coding-conventions 模板到个人工程入口的受控同步关系。

- `docs/reference/evidence-classification.md`：跨场景证据分类及表达边界。工程交付和评审入口引用同一正文。
- `docs/reference/release-version-check.md`：工程交付和评审共用的版本检查规则。

## Generated And Runtime Mapping

- `~/.ai/` ← ai-meta instructions、commands、skills、scripts、config adapter，以及已登记 owner-repo skill 的发现软链；它是本机 aggregation/runtime 层，不是长期事实源。
- `~/.agents/skills/` ← ai-meta `skills/` 与已登记 owner-repo skill 的共享发现软链，供 Codex、Kimi Code 及 Pi 的薄适配入口使用。
- `~/.agents/AGENTS.md`、`~/.pi/agent/AGENTS.md` ← `~/.ai/instructions.md`；`~/.pi/agent/skills/` ← `~/.agents/skills/`。
- 客户端配置目录 ← `install.sh` 发布的最后一跳适配；手工运行态和缓存不得反向成为 repo 事实源。
- `~/.ai/agent-frictions.md`、`~/.ai/frictions/`、`~/.ai/audits/`、`~/.ai/contexts/`、`~/.ai/work-items/`、`~/.ai/loop/`、`~/.ai/skill-verification/`、`~/.ai/rule-evals/`、`~/.ai/usage/` 和含 token 的 MCP 配置是本机私有状态，不进 git。

## Validation

- `python3 -m unittest discover -s scripts -p 'test_*.py'`：scripts、validator、同步器和本机运维入口的主路径回归。
- `scripts/validate-skill <skill-dir>`：上游 skill schema 与 ai-meta invocation / command 集成 gate 的统一入口。
- `scripts/check-skill-invocation-policies`：skill canonical identity、展示元数据和 explicit-only 策略。
- `python3 -m unittest scripts.test_skill_verification`：revision-bound ledger、加载 fingerprint 和 verdict 状态机回归。
- `scripts/private-release check <distribution-root>`：私有发行副本的本机路径、内网标识、身份信息和凭据形态 gate。
- `python3 plugins/route-context/scripts/test_route_context_resolve.py` 与 `python3 plugins/route-context/scripts/test_route_context_hook.py`：context 套件输入侧配置解析和 prompt-time 注入回归。
- `bash install.sh`：发布前预检与本机软链/适配同步。
- `git diff --check`：文档和脚本改动的基础格式检查。

## Architecture Links

- `skills/`、`commands/`、`plugins/`：[Horizontal client consistency](./horizontal-client-consistency.md)。
- `docs/`、`mcp/`、`runtime/`：[Source-of-truth boundaries](./source-of-truth-boundaries.md)。
- skill verification runtime：[Skill Verification Trace](./skill-verification.md)。
- 所有主要 root：[Architecture index](./index.md) 与 [Project map](../project-map.md)。

## Change Guidance

- 新增或重命名顶层 source root、发布入口、runtime mapping 或共享 contract 时，同步本文件和对应 architecture shard。
- 普通 skill、script 或文档内部修改不要求机械更新本文件；只有 ownership、生成关系或主要验证入口改变时才更新。
- AGENTS 只链接本文件，不复制本页目录和职责说明。
