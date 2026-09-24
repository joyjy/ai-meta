# Dispatch Execution

Read only after `agent-assignment` selects RS or internal. Keep the chosen slice, authority, and acceptance fixed while dispatching or recovering from failure. CI observation follows the main skill's mandatory RS handoff and bounded failure rule; the generic executor fallback below never permits mainline CI waiting.

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

Judge savings only against comparable real tasks or a measured baseline. Without one, report the observed result and comparison limit rather than inventing what direct execution would have cost. Carry material findings into the task's existing result or recovery record; do not create a parallel accounting system. Use repeated results to adjust route preferences while preserving responsibility and authority boundaries. This retrospective assessment is not a new pre-dispatch gate.
