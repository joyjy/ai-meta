# Dispatch Execution

Read after `agent-assignment` selects RS or internal, or before dispatching, waiting for, or handling an asynchronous result. Keep the chosen slice, authority, and acceptance fixed while dispatching or recovering from failure. CI observation follows the main skill's mandatory RS handoff and bounded failure rule; the generic executor fallback below never permits mainline CI waiting.

## 异步结果验收与接续

- 按用户目标绑定 exact source / revision、任务所需的验收终态、会改变下一步的状态变化、等待预算和回传任务。
- 可确定性观察默认交给 RS。接入方式、Runtime freshness 和任务生命周期遵循 [RS Desktop push runbook](../../../../rollerskate/docs/runbook/codex-desktop-push.md)。本文件持有主 agent 的验收流程，runbook 持有 RS 接入和传输机制。
- 取得接受回执后，主线继续可独立工作。没有其他工作时结束当前回合，等待结果回传后接续。
- 收到结果后，核对来源、revision 和任务验收条件。再决定完成验收、在原授权内修复，或绑定新的下游观察。
- 观察器报错、超时或回传失败时，对原来源做一次有界核验。业务已到终态时处理结果；否则保留 exact identity、真实状态、接入错误和后续验收条件。
- 分别判断入队、传输接受、执行成功和业务验收。持续推进至用户目标验收完成，或报告明确阻塞。
- 任务内观察和检查沿用原授权，结果消息不扩大授权。用户明确暂停或不等待时遵从。独立长期监控、扩大修复范围和未授权远端写入仍需单独授权。

## 等待预算与失联处理

- pipeline、构建和服务发布开始等待前，必须记录并向用户说明数值预算、开始时间、绝对截止时间及超时动作。优先使用用户或项目明确预算，其次采用来源的 timeout / SLA 或同类运行记录；licloud 构建和服务发布的新观察显式传入 `--checkpoint 300`，5 分钟只表示分段检查点。启用检查点时必须同时显式传入有依据的 `--timeout <总秒数>`；其他场景均无依据时，单次观察默认 pipeline 20 分钟、构建 30 分钟、服务发布 30 分钟。以上均为观察预算，不是业务成功时限。串联阶段须有总截止时间，各阶段预算不得累计突破总预算；启动重试、切换观察器或收到普通进度不能自动重置截止时间。
- 接受回执须绑定 exact source / revision、截止时间、回传任务及可验证的 timeout 回执机制。观察器的工具调用、状态读取和回传也须有界，不能只给业务任务设置 timeout。复用 owner 已有的超时与失败投递入口；不能证明观察与超时回传已接入时，不得声称“会持续等待并通知”，按接入失败收口。
- 业务失败、取消，或观察器退出、报错、失联时，立即按原来源做一次有界核验并回报，不静默等到总预算结束。日志无新增本身不证明失败；用来源状态、心跳或进度时间判断，缺少可信证据则标记 unknown。
- 分段检查点到达时，回传进度变化、仍运行或 unknown。仅当 exact source / revision 不变、来源可查、业务仍运行、授权有效且未超固定总预算时，原 Subscription 自动进入下一段。检查点、重试和进度通知不重置总截止时间；旧观察不回填检查点或自动续期。
- 到达总截止时间必须回传结果；未见终态时按既有失败流程对原来源做一次有界核验，区分业务仍运行、业务失败与观察/回传失败。报告 exact ID / URL、revision、最后可信状态及时间、超时原因和恢复入口。超时不能算成功，也不能仅据超时宣称业务失败；不自动取消、重启、重新发布或延长预算。仍在原授权内且有明确错误证据的修复可继续，总预算耗尽后续等须明确给出新的预算与依据，独立长期监控仍需单独授权。
- 验收终态必须匹配目标：pipeline 成功核对绑定 revision 和必需 jobs；构建核对退出状态及目标产物 identity；服务发布核对目标环境运行的 revision、发布终态和 health/readback。触发成功、构建成功或传输接受均不能替代服务发布验收。

## CI Observation

- `direct`、小任务和完整上下文依赖不豁免 CI 观察交接。首次发现相关 pipeline/job 为 `pending/running` 后，只为补齐绑定读取缺失事实，不再查询同一状态或主线等待。同一 source/revision 的相关 job 合并为一次观察和所需终态条件；验收确需独立 job 身份时才单独绑定。
- 实际取得 RS 接受回执并核对 source/revision 与回传目标后才算交接。主线继续独立工作或结束当前回合，由回传接续；新 pipeline/job 重新绑定，绿灯仍须核验用户目标。
- 主线不以 `sleep`、shell/API watch、循环、重复状态读取或延长工具等待观察 CI。RS 报错、超时或回传失败时，对原来源做一次有界核验：业务已终态则处理结果；仍未结束则保留 exact identity、真实状态、接入错误和后续 oracle，后续接续沿用该 identity，不退回主线轮询。

## Route Identity

- Use current callable model IDs. DS fast is `pi-ds-flash` → `deepseek/deepseek-v4-flash`; DS pro is `pi-ds-pro` → `deepseek/deepseek-v4-pro`. Confirm actual Agent registration and provider/model configuration on first use, cache invalidation, or route change, not before every small task.
- Internal delegation must pass the selected model and reasoning effort explicitly with `fork_turns: "none"` or a positive recent-turn count. Do not inherit the mainline model through a full-history fork. A Sol worker must meet the main skill's same-model benefit gate.
- For the first two tiers, prefer an available, healthy RS route for a bounded responsibility whose result replaces substantive mainline investigation, review, or verification and needs only sampled acceptance. External quota offload is an additional benefit, not a prerequisite. Use the corresponding internal tier only after the main skill's pre-dispatch net-benefit gate is satisfied. Mere decomposability is not enough for internal dispatch. Do not treat Codex or EPT as an external quota-saving route; use the fewest participants and configure steward/worker only when decomposition and synthesis require it.

## Preflight And Handoff

- Resolve RS through the configured tool route and use a read-only preflight for the exact task as the capability and health check. Before start, bind exact Agent, workspace/revision, effect, acceptance, wait budget, and return path. A failed preflight names the concrete obstacle; do not infer unavailability from an unchecked route. If the runtime version or capability is unsuitable, compare direct and internal again; do not repair or upgrade RS inside the business task.
- Verify rule delivery for the selected client and Run rather than assuming that Codex, Kimi, and Pi load the same global instructions or skills. Include only the applicable rule source/revision and acceptance in the immutable brief. A prompt reference alone is not proof of loading or Host enforcement; keep effects read-only when a write, Git, deletion, or external-action boundary depends on an unverified personal rule.
- GitLab Pipeline 等待先读取 `~/.ai/tool-routes.md` 的「GitLab Pipeline 异步接续」；该路由拥有类型化入口、exact binding、preflight 和失败收口。不得临场生成 watcher 或改 registry 绕过路由结果。
- Dispatch an immutable brief or evidence index with the goal, exact repo/revision, evidence entrypoints, constraints and authority, expected artifact, and acceptance. Include only facts needed for this responsibility; if reliable execution requires the full mainline context, keep that responsibility direct as specified by the main skill. For a delegated responsibility, the worker reads additional evidence as needed. Follow-ups carry only deltas, reusable results, and remaining gaps.
- Return the conclusion, changed artifact or evidence location, checks, and unresolved issues. The main agent samples acceptance evidence and consumers rather than repeating the entire delegated investigation or implementation.

## Failure And Writer Switching

- On admission failure, execution failure, timeout without usable output, or rejected output, query the original route once for bounded status. Preserve exact Run/Agent/revision, error, and artifact location; decide whether existing output is reusable and which executor owns the remaining responsibility.
- Recompare mainline takeover, internal completion, or same-tier rework. Do not mechanically fall back to internal, retry the external route in the same task, or diagnose its adapter/session.
- Before switching a write task, prove the old writer stopped and inspect its changes and side effects. While status is unknown, only non-conflicting read-only work may continue; overlapping writes stop at the identity/state checkpoint.
- If internal completion also fails acceptance, the main agent narrows the exact gap and may suggest Astra only for a user decision. Do not cycle models. Mainline takeover is reserved for unavailable internal tools, writer conflict, non-transferable runtime state, or a remaining single-step dependency.

## Effectiveness Evidence

The main agent owns the per-task evidence: at acceptance or terminal failure, retain exact worker/run identities and available usage/result receipts in the existing task result or recovery record. Workers return their normal result and receipt; they do not create an accounting workflow. The main agent reports observed mainline Sol/Codex usage, all Codex worker usage, external-provider usage, elapsed delivery time, handoff/acceptance work, and rework when available. Use existing receipts and usage records; unavailable measurements stay unknown. Cross-task comparison belongs to the existing work-review process, using these exact identities rather than requiring each delivery task to perform a historical study. Distinguish shifting work to another Codex agent from reducing Codex consumption, and token usage from monetary cost.

比较模型时按实际执行轮次绑定 model / effort，不把聊天当前配置或混合模型任务的结果全部归给一个模型。记录任务复杂度、上下文条件、验收及用户催促或主线返工；把环境阻塞、观察器和回传失败与模型判断或执行失误分开。报告生成、工具退出 0 和 worker 自报成功不能替代调用方验收。缺少同类对照、effort 不同或仅有少量样本时，保留这些限制，不据此推导模型代际优劣。

Judge savings only against comparable real tasks or a measured baseline. Without one, report the observed result and comparison limit rather than inventing what direct execution would have cost. Carry material findings into the task's existing result or recovery record; do not create a parallel accounting system. Use repeated results to adjust route preferences while preserving responsibility and authority boundaries. This retrospective assessment is not a new pre-dispatch gate.
