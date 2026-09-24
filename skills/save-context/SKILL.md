---
name: save-context
description: "Create an explicit recovery checkpoint for a project or workstream, optionally syncing durable knowledge and a substantive Daily Note entry. Use when the user explicitly asks to save context, 保存上下文, pause or switch work, preserve the current session for later recovery, or recover a stuck thread. Do not trigger merely because a request changes an existing context file or route state; narrow mutations such as clearing a Next Step, parking a workstream, or correcting one context field are not a save-context checkpoint."
disable-model-invocation: true
---

# save-context

只执行用户明确要求的恢复 checkpoint；单字段 route/context 维护不构成 checkpoint。保存恢复状态、归位后的 durable facts/objective friction，以及有实质进展时的一行 Daily Note；原始对话留在客户端。

## Direct References

按 route 和输出面只读命中的一层 reference；existing route 的普通 checkpoint 不读 routing/schema：

- `references/context-routing.md`：仅 route 未知/歧义、新建 workstream 或 closure。
- `references/context-schema.md`：仅新建或修复完整 context.v3 / workstream payload。
- `references/context-io.md`：仅非 Codex client、legacy 调用或特殊 I/O flags。
- `references/durable-sync.md`：layer ownership、durable edit、friction/tool route、commit boundary。
- `references/timeline-title-output.md`：仅 substantive timeline 的确定性边界，或历史/批量 title maintenance。
- `references/final-form-state.md`：仅保存已确认或明确要求的 final-form。
- `references/offline-recovery.md`：仅恢复 stuck/interrupted task。
- `references/temporary-outputs.md`：仅本轮或选中 route 存在 agent 自建临时输出。

## Safety Gates

- 不 silent save，也不 silent close/promote/delete 普通或 ambiguous workstream。唯一窄例外是当前 session 已直接证明 exact context-backed final-form 的 goal、acceptance、checks 和 authorized exit actions 均完成，并按 `context-routing.md` 的 exact-goal helper 清理。
- commit 按全局 Git 边界执行，保存前检查见 `durable-sync.md`；永不因此获得 push 权限。
- 不为了记录完成历史或 timeline 而覆盖 recovery snapshot。
- 私人/local workflow facts 不进入 team/external repo 的 `AGENTS.md`。
- 保留恢复所需的 paths、tools、URLs、worktree/generated output 和下一入口；unfinished state 不得丢失。
- durable advisory 或 friction finding 不授权未请求的源码、文档、删除或远端写入。

## Workflow

1. **Resolve route**：使用显式 abbr，否则读 project `index.md`；仍未知时询问。已知 mainline/existing workstream 直接继续；未知/歧义、新建 workstream 或 closure 才读 `context-routing.md`。仅查询 route 时不加载 writer。
2. **Classify facts**：区分 global preference、tool route、agent friction、project docs 和 temporary recovery state。durable facts 写回 owner，context 只留恢复入口；无安全 owner 时标记 `pending durable home`。需要 durable edit 时读取 `durable-sync.md`。
3. **Admit before writes**：回读当前任务已涉及的 source owner（如 MR/Pipeline、runtime revision、未完成副作用和 blocker），不横扫无关项目。生成 `save-context.admission.v1`；仍能处理的 failure、stale runtime 或副作用记为 `continue_work` + actionable，外部阻塞留在 Blocked。明确暂停/切换/保存未完成现场时直接用 `--pause-override` 保存 Doing/Blocked；普通保存发现新 actionable 时先继续处理。override 不绕过 identity、input validation 或其他 authority，也不表示交付完成。
4. **Settle authorized outputs**：只处理本 session 新增且已授权的 durable facts。存在 agent 自建临时输出时读 `temporary-outputs.md` 完成保留或清理；其他 cleanup deletion 始终独立授权。
5. **Checkpoint once**：仅在 recovery/route/critical facts 变化或用户要求 refresh 时写。Codex 将完整 context markdown 或 `context.workstream.v1` payload 写入 `/private/tmp`，再用 `~/.ai/scripts/save-context --orchestrate <abbr> --admission-file <file> --context-file <file> [--timeline "[HH:MM-HH:MM] ..."] [--pause-override]` 一次完成 admission 与 context/timeline；脚本合并 workstream 并保留其他 route。新建/修复格式才读 `context-schema.md`；有 timeline 时读 `timeline-title-output.md`。只有 work-log 价值时读 `context-io.md` 的 timeline-only 路径，均无价值则 skip；清理本轮临时文件并核对 `save-context.checkpoint.v1` receipt。
6. **Refresh title**：context stage 成功后，通过原生能力更新 exact current task；禁止写 Codex SQLite/index。保持 `[abbr][MMdd] <summary>`，summary 取 primary substantive user goal，不取 load/save/exit 控制词。失败不回滚 checkpoint。
7. **Report**：按 receipt 先报 saved/partially saved/blocked、changed paths 和下一恢复入口，单列 title changed/unchanged/skipped/failed；`continue_work` 不得称为已保存。最后一句固定为“保存完成了，站起来活动一下身体，上个厕所喝点水。”

## Offline Recovery

旧 Codex thread 太长、stuck 或已中断时，不要求原 thread 自救。在新 thread 按 `references/offline-recovery.md` 生成 bounded recovery packet，再重建 clean context；只有特定 span 证据不足时才回读原始 rollout 行。

## Completion Standard

- route 与 YAML/Markdown 一致；Doing 不留完成项，不发明 fallback Next Step。
- active workstream 未被误关；durable facts 未复制进 context，恢复入口完整。
- admission 先于所有输出；`continue_work` 时不得写 checkpoint 或 title，除非用户明确授权 `--pause-override` 后成功。
- context 预检/写入失败保持非零；title 失败在 receipt 外报告，不撤销已成功的 checkpoint。
- 用户能看出保存了什么、写到哪里、哪些未保存以及下次从哪里继续。
