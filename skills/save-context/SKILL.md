---
name: save-context
description: "Create an explicit recovery checkpoint for a project or workstream, optionally syncing durable knowledge and a substantive Daily Note entry. Use when the user explicitly asks to save context, 保存上下文, pause or switch work, preserve the current session for later recovery, or recover a stuck thread. Do not trigger merely because a request changes an existing context file or route state; narrow mutations such as clearing a Next Step, parking a workstream, or correcting one context field are not a save-context checkpoint."
disable-model-invocation: true
---

# save-context

只执行用户明确要求的恢复 checkpoint；单独清理 Next Step、park/reopen workstream 或修改一个 context 字段不构成 checkpoint。保存恢复状态、归位后的 durable facts/objective friction，以及有实质进展时的一行 Daily Note；原始对话留在客户端。

## Direct References

先确定 route 和实际输出面，只读取命中的一层 direct reference：

- `references/context-routing.md`：route、closure、context.v2、fixed writer、offline recovery。
- `references/durable-sync.md`：layer ownership、durable edit、friction/tool route、commit boundary。
- `references/agent-audit.md`：Codex audit dispatch、receipt、settlement 和 follow-up。
- `references/timeline-title-output.md`：timeline、Daily Note、native task title 和 final output。

## Safety Gates

- 不 silent save，也不 silent close/promote/delete 普通或 ambiguous workstream。唯一窄例外是当前 session 已直接证明 exact context-backed final-form 的 goal、acceptance、checks 和 authorized exit actions 均完成，并按 `context-routing.md` 的 exact-goal helper 清理。
- commit 只按 `durable-sync.md` 的窄 source-artifact exception 和全局 git 规则执行；永不因此获得 push 权限。
- 不为了记录完成历史或 timeline 而覆盖 recovery snapshot。
- 私人/local workflow facts 不进入 team/external repo 的 `AGENTS.md`。
- 保留恢复所需的 exact paths、tools、URLs、worktree/generated output 和下一入口；unfinished state 不得丢失。
- durable advisory、audit 或 friction finding 不授权未请求的源码、文档、删除或远端写入。

## Workflow

1. **Resolve route**：使用显式 abbr，否则读当前 project `index.md`；仍未知时询问。区分 mainline、existing/new workstream 和 completed small task；歧义会改变写入目标时只问一个问题。仅在 route 未知/歧义、需要写 context 或判断 closure 时读取 `context-routing.md`；显式 route 的 timeline-only checkpoint 不加载它。
2. **Classify facts**：区分 global preference、tool route、agent friction、project docs 和 temporary recovery state。durable facts 写回 owner，context 只留恢复入口；无安全 owner 时标记 `pending durable home`。需要 durable edit 时读取 `durable-sync.md`。
3. **Admit checkpoint before writes**：回读当前任务已涉及的 source owner（如 MR/Pipeline、runtime revision、未完成副作用和 blocker），不横扫无关项目。生成 `save-context.admission.v1`；存在可继续处理的 failure 或 stale runtime 时用 `continue_work`，在所有写入前 fail closed。仅当用户看见 blocker 后仍要求暂停，才用 `--pause-override`。
4. **Prepare audit**：Codex 按 `agent-audit.md` 绑定 exact source、route、cwd 和可选 ledger；紧接 engineering-exit 时复用其 handoff。编排器先只读预检输入，再由 save-context 单次 dispatch；结果留给后续 save 或显式 follow-up 结算。非 Codex client 跳过。
5. **Settle authorized outputs**：只处理本 session 新增且已授权的 durable facts。auditor 只提议，主 agent 验证并结算；cleanup deletion 始终独立授权。
6. **Checkpoint once**：仅在 recovery/route/critical facts 变化或用户要求 refresh 时写。Codex 用 `context-routing.md` 的 fixed orchestrator 一次完成 admission、audit、context/timeline；只有 work-log 价值时 timeline-only，均无价值则 skip。
7. **Refresh native task title**：receipt 的 context stage 成功后，按 `timeline-title-output.md` 原生更新 exact current task；禁止写 Codex SQLite/index。失败不回滚 checkpoint，但必须报告。
8. **Report**：有实质进展时读取 `timeline-title-output.md`，按 receipt 报告脚本阶段并单列 title 结果；本轮不轮询 audit。`continue_work` 不得报告为已保存。

## Offline Recovery

旧 Codex thread 太长、stuck 或已中断时，不要求原 thread 自救。在新 thread 按 `context-routing.md` 生成 bounded recovery packet，再重建 clean context；只有特定 span 证据不足时才回读原始 rollout 行。

## Completion Standard

- route 与 YAML/Markdown 一致；Doing 不留完成项，不发明 fallback Next Step。
- active workstream 未被误关；durable facts 未复制进 context，恢复入口完整。
- admission 先于所有输出；`continue_work` 时不得写 checkpoint 或 title，除非用户明确授权 `--pause-override` 后成功。
- context 预检/写入失败保持非零；audit 失败形成 `degraded` receipt，title 失败在 receipt 外报告，均不撤销已成功的 checkpoint。
- 用户能看出保存了什么、写到哪里、哪些未保存以及下次从哪里继续。
