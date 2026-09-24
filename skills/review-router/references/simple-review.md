# Simple Review

对固定 target、behavior、context、evidence 做 maintainer pass。

- 优先 correctness bug、regression、缺失 acceptance/test 和高风险边界；只读足以判断 material concern 的 context。
- Finding 锚定最窄 file/line、hunk、test 或 evidence；报告 P0/P1 和 material P2，含 impact、evidence 与 correction/decision，省略偏好、低影响整理、checklist narration 和臆造问题。
- Next strategy 只选最可能改变 readiness 的一个：spec/scope/standards 未决用 `two-axis`；架构/安全/性能/依赖/data-contract 风险用 `quality`；可删除、native/stdlib 替代、投机抽象或显著 shrink 用 `prune`；真实 invocation/artifact/permission/deployment/lifecycle/consumer 未被证明用 `challenge`；目标与行为一致、checks 覆盖主路径且无 material uncertainty 用 `none`。不要因 size/checklist 升级。

输出 `strategy: simple`、`verdict: pass|findings`、findings 或 `no material findings`，以及 `next_review.strategy: none|two-axis|quality|prune|challenge`、reason 和非 `none` 时的 exact unresolved question。P0/P1 阻止 readiness；P2 与 fixes 归 caller。
