# Changelog

本文件记录 ai-meta 已完成的项目历史。当前未完成事项保留在 [`index.md`](index.md)。

## 2026-09

- [x] (2026-09-11) review-router 明确区分增量复审、完整交付、模块整体与全仓审查；范围先于策略，无 diff 可审现有实现，结论须说明覆盖和遗漏。静态 gate 通过，实际行为按最终指纹采样。

- [x] (2026-09-10) 修复 Context Stop 同一 MR 重复裸引用误报：本条回复中已有一次链接即可，遗漏按 MR URL 去重；补齐链接后紧接中文标点的提取边界和回归。
- [x] (2026-09-10) 将 e3e1505 脱敏同步到 GitHub 发行仓库；检查账号下 18 个仓库的各分支作者历史，为发行 checkout 单独配置 GitHub noreply 身份并重写其 7 条提交，远端 author/committer 均关联 joyjy。发行仓库保留私有中转用途。

- [x] (2026-09-10) 将 route-context 扩为 Context 套件，补齐标准 hooks 发现入口与单次 MR 漏链补正；真实 Codex 样本通过。审查 15 个自维护技能入口，收敛全局/项目规则归属、暂停保存授权、条件加载与停止门槛；静态验收通过，技能行为仍按版本采样。

- [x] (2026-09-10) 恢复显式 engineering-exit 的当前 scope commit、push、MR/PR 交付授权，保留普通实现仅自主 commit、local-only/prepare-only 限制及 merge/force push 单独授权；全局规则、技能入口与 MR reference 同步对齐。

- [x] (2026-09-09) 收束 context.v3、按项目展示仓库维护提醒、final-form 验收约束与 skill verification 台账；补齐加载时全部 artifact 指纹校验，Java formatter hook 在工作区有未暂存改动时提前停止。静态验证通过，skill 行为效果继续由匹配版本的真实样本验证。
- [x] (2026-09-09) 明确已授权纠错连续执行、缺授权时主动询问具体下一步；补齐 GitLab snippet 的 CLI 读取路由。取消独立 audit Subscription 改造和旧 MCP 迁移工具扩展，完成 LL 预算待办；按用户决定完成 freshness 待办，后续问题由每日分析跟进。
- [x] (2026-09-02) 将 save-context 标题刷新从 Codex 本地 SQLite/index 旁路写入迁移到客户端原生 task rename capability；脚本 receipt 不再伪报标题阶段，旧 `codex_session_titles.py` 写模式 fail closed，仅保留 dry-run inventory

## 2026-08

- [x] (2026-08-05) 完成 agent-facing 文档治理：移除已退出发布路径的 `my-bmad-*` commands 与旧手册，收敛 README 运行细节和 context contract 摘要，把 GitLab MR description / artifact 与 Gradle wrapper 首次执行门禁注入 route-context，并将 tool-routes 的 GitLab 操作手册下沉到 helper README

## 2026-07

- [x] (2026-07-20) 对照 Matt Pocock skills v1.1.0 复盘 grill、handoff 与 repo setup；仅为本地 `grill` 增加 decision-frontier 退出条件，不引入上游 reference、handoff 或 setup
- [x] (2026-07-13) 新增 objective agent friction observability：从 Codex rollout 安全提取候选事件，由 `save-context` 记录、`load-context` 计数提醒、`engineering-exit` 人工结算，并支持 ownership 和 retention dry-run
- [x] (2026-07-13) 补齐 `ff` / Loop Ledger 到 Codex goal adapter 的显式 contract 绑定，新增 agent loop topology、goal objective renderer 和 verifier 约束
- [x] (2026-07-13) 将 `route-context` 扩展为可区分 mention / execute 的议会执行路由，刷新 Codex plugin，并完成 README 卖点与外置记忆分享稿收束
- [x] (2026-07-07) 收敛 `/ll` 为薄 command + skill source of truth，新增 `/loop` 开始和 `save-context` 完成后的身体活动提醒
- [x] (2026-07-07) 新增 `grill` 连续追问 skill，强化 `ff` work order 的 verification loop、冷启动验证和结构性回归捕获
- [x] (2026-07-07) 将设计方向从 coding-conventions 拆到 `dd`，新增 Design Baseline 恢复模式和 specialist design lens 路由
- [x] (2026-07-07) 收紧 doc-arch / agent-doc-hygiene 的 README 去重、ADR admission 和 decision-record 边界
- [x] (2026-07-07) 更新 GitLab API 查询路由，记录 GTD 与 arch-hub 两套 cache/broker owner 边界

## 2026-06

- [x] (2026-06-15) 新增 `tool-routes.md` 默认工具入口层，并将全局 `instructions.md` 重排为 agent-friendly 的启动/安全/路由/上下文/协作结构
- [x] (2026-06-15) 新增 `gitlab-inline-comment` helper：通过 GitLab Discussions API 创建 MR diff 行内评论，替代 experimental `glab mr note create --file` 默认路线，并将对应 agent friction 标记为 resolved
- [x] (2026-06-15) 新增 Agent 运行摩擦层：`src/agent-frictions.md` 记录可复现工具/路由 fallback 与改善候选，`save-context` 自动发现并维护，旧 pitfall 中 Shell 网络/sandbox 与 GitLab MR 行内评论工具不稳定项归为 friction
- [x] (2026-06-12) coding-conventions 新增 CLI 工程模板：约束 parser/dispatch 边界、command module 顺序、写操作 preview/confirm/execute、API/support 模块边界、可恢复状态和命令级测试
- [x] (2026-06-12) 收紧 save/load context 空状态输出；coding-conventions 增加个人默认层、团队项目边界、README/AGENTS/CLAUDE 分工、前端 loading/防抖/防重放和 GitLab MR 项目配置审计；全局规则补充删除前二次确认
- [x] (2026-06-11) 梳理 repo 内 AGENTS.md 的职责边界：项目架构约束为主，编码规范保持薄层，并评估个人 coding-conventions 注释对其他开发者环境的影响
- [x] (2026-06-11) 清理 `agent-status` 本地看板源码与发布入口；瘦身 `load-context` skill；coding-conventions 补 MR 行内评论、UI 协作、tmux dev server 约定；将无权限或低频 Lark skills 移出 Codex 可发现目录
- [x] (2026-06-11) 新增 `document-slimming` skill 作为低频手动文档瘦身入口；`index.md` 只保留当前 Backlog，已完成历史迁入一级 `changelog.md`
- [x] (2026-06-09) coding-conventions 新增 `/cc` 薄命令、校验模式，以及 frontend / design 模板；design 模板收敛为风格延续、图标统一、真实文本可选中等偏好
- [x] (2026-06-09) 强化全局澄清规则：探索状态禁止直接实现，grill / stress-test 作为澄清升级层并保持一轮一个关键问题
- [x] (2026-06-09) 收敛 Claude/OpenCode save/load 入口：只发布 slash command，save/load skill 仅作为 command source of truth 与 Codex 可发现 skill
- [x] (2026-06-09) 修正 load-context 项目入口兜底：支持从项目 index.md 的 Source / Links 匹配当前 repo 路径或 remote，而不只按 basename 推断
- [x] (2026-06-04) 修正 Codex title refresh 项目识别规则：当前项目应识别为 `sma` 时误生成 `[amt]` 前缀

## 2026-05

- [x] (2026-05-29) 修正 save-context 分层兜底：项目缺少 ADR/decisions/backlog 承载层时，关键事实先以 `pending durable home` 保留在 context，不直接丢弃
- [x] (2026-05-29) 纳管 `~/.ai/` 核心源文件：`src/instructions.md`、`src/hooks/`、MCP redacted 模板入 repo，`install.sh` 发布为软链；contexts 与含 token MCP 配置保留本机运行态
- [x] (2026-05-29) 将 MCP endpoint/token 配置纳入共享层：`~/.ai/mcp/config.json` 成为跨 Claude/OpenCode/Codex 桥接的本机 source of truth，工具私有配置只做适配或 fallback
- [x] (2026-05-28) 修复 Codex session title 脚本误判 `[codex]`：收窄 codex abbr 规则、过滤 load-context skill 链接参数噪声，并重刷历史标题
- [x] (2026-05-28) 将文档终态原则推广到全局 `~/.ai/instructions.md`，ai-meta 入口改为引用全局原则并保留项目落点
- [x] (2026-05-28) 回顾并收敛纳管文档一致性：统一 AGENTS/current topology/context 分线表述，新增终态事实原则减少 context 分析推导
- [x] (2026-05-28) save-context 新增非破坏性保存规则：快速任务只补 timeline 时使用 `--timeline-only`，不重写未变化的 context 快照
- [x] (2026-05-28) 收紧 Codex session title 刷新脚本：`--all` 默认只修坏标题和 DB/index 不一致，新增 `--force-reinfer` 才全量重推断
- [x] (2026-05-28) 修复 Codex session title 刷新脚本：忽略 skill 注入与 Markdown skill 链接噪声，并补齐 DB/title index 同步
- [x] (2026-05-28) Java/Gradle 编码约定新增 Logging：每个 action 在必需参数读取/校验完成后先写入口日志
- [x] (2026-05-28) Java/Gradle 编码约定新增 Code Style：进入方法体后第一条语句前保留空行
- [x] (2026-05-28) coding-conventions 新增 Python 模板：修改 `.py` 后用 YAPF Google style 执行格式化与格式检查
- [x] (2026-05-28) git 规范补充：agent 不默认创建 `git worktree`，创建前需明确用途、路径和清理方式
- [x] (2026-05-28) `~/.ai/agents` 按客户端分层：OpenCode 指向 `~/.ai/agents/opencode/`，Claude Code 指向 `~/.ai/agents/claude/`，避免不同客户端共用冗余 agent frontmatter
- [x] (2026-05-27) coding-conventions 新增 pitfall 记录规则；general 模板补 Shell/CLI 网络通道与长文本参数 pitfall、项目指令入口一致性规则，并将项目指令入口检查提升到全局指令
- [x] (2026-05-27) 登记 `symphony-lite` 为独立 AI 系统模块，与 `larkbot` 同级；ai-meta 只维护项目地图和 `~/.ai/` 接入边界
- [x] (2026-05-27) save/load context 改为 skill 作为 source of truth，command 仅作薄入口；save-context 支持主线/分线快照、收束询问与删除
- [x] (2026-05-27) Java/Gradle 编码约定新增文档目录规则：既有 `/doc` 保持 API 文档用途，讨论/设计/分析文档放 `/docs`
- [x] (2026-05-27) 新增 agent-status 单屏进度雷达：聚合 context、GTD 固定产物、repo dirty 状态和可选进程列表，仅发布为 scripts，不作为 command 或 Codex skill
- [x] (2026-05-26) 建立个人 AI 系统分类地图：AI 系统模块 / 工作域 / 子模块 / 任务，明确 `gtd` 为工作域、`coding-conventions` 为 `ai-meta` 子模块
- [x] (2026-05-26) 将 save/load context 包装为 Codex skills：新增 `src/skills/save-context`、`src/skills/load-context`，安装到 `~/.agents/skills/`
- [x] (2026-05-14) java-gradle 模板 Code Style 新增：避免业务自定义 magic number 规则
- [x] (2026-05-11) git 规范补充 MR 流程规则（approve、禁止 agent 合并、评审意见逐条确认、API 鉴权 checklist）；java-gradle 新增安全规范 section；coding-conventions skill 支持接受输入更新模板
- [x] (2026-05-11) coding-conventions skill 扩展：git 模板 + sync-conventions.sh 幂等展开脚本
- [x] (2026-05-07) coding-conventions skill：java-gradle 模板（verify/覆盖率/pre-commit），install.sh 补 src/skills 软链
- [x] (2026-05-07) 删除 AGENTS.md 中"每次会话开始执行 load-context"规则
- [x] (2026-05-07) 加入 Codex CLI 支持：install.sh 补软链、架构图更新、三工具接入对照表、CLAUDE.md 新建
- [x] (2026-05-07) save-context 决策三路分类（约定性/架构性/一次性）+ backlog latest first + 完成日期
- [x] (2026-05-07) 项目结构重构：commands→src/commands，decisions 内嵌到 architecture.md ADR，manual/ 独立，补 prd/architecture，install.sh 发布为软链
- [x] (2026-05-06) my-bmad-* v2：对齐官方 BMAD-METHOD，作为薄包装层复用官方 skill，新增 init/create-story 命令，story 状态机 5 步，epics.md 单文件，扁平 sprint-status
- [x] (2026-05-06) 需求编号格式对齐 BMAD 官方：FR1/FR2（无连字符），NFR 改按类别分组，同步 4 个命令 + 手册
- [x] (2026-05-06) my-bmad-* 完善：手册补充 Epic/Sprint 划分原则、Decisions 约定、跨文件关联
- [x] (2026-05-06) 建立项目文档工作流：实现 my-bmad-* slash 命令体系，替代 BMAD subagent 安装
- [x] (2026-05-06) /save-context v2：四层知识分层同步，防止文档腐化
- [x] (2026-05-06) 整理 ~/.config/opencode/AGENTS.md
- [x] (2026-05-06) amt 改为纯文档 AGENT.md，移除 subagent
- [x] (2026-05-06) 接入 Claude Code commands
- [x] (2026-05-06) 验证 /load-context 在 OpenCode 可用
- [x] (2026-05-06) 创建 agents/amt.md，描述 ~/.ai/ 架构全览
- [x] (2026-05-06) 完成 /save-context slash 命令
