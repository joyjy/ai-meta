# Evidence Classification

Use this reference as the shared evidence-boundary model when a conclusion may
affect implementation, deletion, commit readiness, release risk, architecture
findings, external-source interpretation, or promotion of a reusable rule.

Do not require every user-facing sentence to carry a label. The goal is to keep
evidence levels distinct so the agent can decide what needs confirmation,
reviewer attention, or explicit risk acceptance.

## Categories

- `KNOWN`: directly observed from the user, repo files, tool output, official
  sources, original posts, or other cited primary material.
- `COMPUTED`: calculated from known inputs, such as line counts, diff stats,
  test totals, dates, or deterministic script output.
- `INFERRED`: reasoned from known evidence, but not directly observed.
- `COMMON`: general technical or domain knowledge that was not verified in the
  current turn.
- `FRAME`: true inside an explicit model, policy, tool contract, or proposed
  framework, but not automatically true in the real system.
- `GUESS`: weak hypothesis or placeholder. Avoid using it as a decision basis.

## Use

- Treat `KNOWN` and `COMPUTED` as the strongest evidence.
- Treat `INFERRED` as actionable only when the supporting evidence is visible.
- Treat `FRAME` as conditional; do not let a framework assumption become a fact.
- Treat `COMMON` as useful context, not proof.
- Treat `GUESS` as a prompt to verify, ask, or leave a follow-up.

Classify material conclusions internally before deciding readiness, severity,
promotion, or follow-up. Do not add a second workflow state machine or replace
domain fields such as `agent proved`, `blocking question`, or `Watch`.

Use explicit labels only when a durable or research artifact mixes evidence
levels and a later reader could otherwise reuse an inference or frame-bound
claim as fact. Emit only populated, decision-relevant categories; never label
every sentence. Keep `GUESS` out of acceptance, readiness, promoted rules, and
publishable conclusions.

Prefer domain language in user-facing output:

- review and release: `已证明` / `未证明` / `需要人工验证`;
- external research: `来源事实` / `分析推断` / `框架映射`;
- pattern promotion: `真实命中` / `独立复现次数` / `可迁移性判断`.
