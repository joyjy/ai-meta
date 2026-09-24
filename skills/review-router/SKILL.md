---
name: review-router
description: Route rr code/MR/PR, module, whole-repository, simplification and explicit design reviews. Excludes ordinary document requests and feedback triage.
---

# review-router

先固定 scope、identity 和 baseline，再选 strategy。只读输出 findings、verdict 与一个 next-review decision；不修复、删除或写 Git/远端/持久状态，也不代替 release gate。`rr` 只是用户别名。

## Scope

从用户请求和对话确定 decision，不用最近 commit 或方便的 dirty diff 代替。开头简述 scope、target、baseline（或 snapshot）：

| Scope | Boundary |
| --- | --- |
| Incremental re-review | reviewed revision 后的变化、未解决 finding 及受影响消费者；baseline 缺失先解析，不静默用 `HEAD~1`。 |
| Complete delivery | delivery baseline 后的 task-owned commits、dirty、消费者及集成证据；MR/PR 绑定真实 base/head，区分未发布 local follow-up。 |
| Existing module | 当前实现、职责、依赖、兼容和相关 caller；无需 diff。 |
| Whole repository | 已识别 repo 的代码、文档、依赖/build 配置与验证入口；不得缩成近期 diff 或单模块。 |

增量和完整交付都追踪 concrete contract/consumer，但不等于全仓审计。模块/全仓先画结构与 owner，再按风险深入；每个顶层区域记 inspected、sampled 或 excluded（含原因），generated/vendor 追到 source owner，并区分既有债务与本次新增。Sampling 不证明穷尽正确，空 diff 不终止 snapshot review。

先查可查事实，只在余下歧义改变 scope 时提问。空 change diff 不代表旧 finding 消失，也不授权切到 repo scan；单 commit 或 `HEAD~1` 只能由用户明确选择。

## Baseline

绑定 acceptance/spec、适用标准、diff/snapshot、context 与验证证据。Evolution 还需 caller-owned revision、fingerprint、round 和 prior findings。

显式 `design` 绑定 file/section/proposal、problem、constraints、current anchors 与 decision question；无需 diff。根据现实验证 rationale，缺少关键 decision 可判 `not-ready`。

## Strategy

- 显式 strategy 优先且只运行该 strategy，包括 `simple`、`design`。
- Plain `rr` / `rr auto` 不因 Markdown/proposal 推断 design。
- Refactor、架构治理、KISS/DRY、拆分或 code health → `quality`。
- 删除、YAGNI、native/stdlib 替代或过度设计 → `prune`；更广的架构、安全、性能风险 → `quality`。
- 其他 plain/auto 和 `caller=engineering-exit` → simple，最多一次 evidence-backed escalation；caller 负责 disposition。
- 没有 material question 时选 `none`；size/checklist 不构成升级理由。

## Direct Routes

- **Simple**：`references/simple-review.md`，maintainer pass + next strategy。
- **Design**：`references/design-review.md`，proposal semantics + feasibility。
- **Challenge**：`references/challenge-review.md`，real-consumer proof。
- **Evolution**：`references/evolution-review.md`，需 caller-owned round state。
- **Two-axis**：`~/Documents/reference/matt-skills/skills/engineering/code-review/SKILL.md`，独立 Spec / Standards passes。
- **Quality**：`~/Documents/reference/addy-agent-skills/skills/code-review-and-quality/SKILL.md`，只读 `The Five-Axis Review`、`Review Process`、`Verification` 并选择 material axes。
- **Prune**：`~/Documents/reference/ponytail/skills/ponytail-review/SKILL.md`，标记 `delete|stdlib|native|yagni|shrink`、给 replacement、按 reduction 排序，结尾 `net: -<N> lines possible.` 或 `Lean already. Ship.`。无证据的 rejected-scope residue 也算；accessibility、data-loss prevention 和最小 runnable check 不算 bloat。

External lens 只继承上述窄 contract，不继承 tracker/client workflow；缺失时按本条 contract 执行，不搜索或安装替代。

## Evidence And Result

- 混合 observation、calculation、inference 或 framework assumption 时读 `../engineering-exit/references/evidence-classification.md`；只有 direct/computed evidence 证明 claim，其余须限定。
- 保留 strategy 的 verdict、词汇与 required sections，不压平成 simple。
- Findings 按 severity 在前，锚定最窄 file/line、artifact 或 evidence，说明 impact 与 correction/decision；无实质问题写 `no material findings`。报告 coverage/omission；snapshot scan 含 area accounting，不堆 raw inventory/tool narration。
- 结尾必须有 `next_review.strategy: none|two-axis|quality|prune|challenge`、evidence-backed reason，以及除 `none` 外的 exact unresolved question。
- Recommendation 不授予 fix 或扩 scope 权限；domain/release/security gate 仍归 owner。Design 保持 one-shot/read-only，不替代 `doc-arch-review` 或变成 grill/steelman。
