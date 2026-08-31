---
type: Reference
title: Gates and release preflight
description: Shallow specialist gates, gitlab.flow levels, and release-quality preflight boundaries.
resource:
tags: [ai-meta, architecture, gates, release]
---

# Gates And Release Preflight

## Scope

本文件记录 ai-meta 垂直 ll 中的浅 gate：agent 文档治理、架构文档评审、release preflight 和 `gitlab.flow` 工程收束等级。

## Current Facts

skill 采用浅链路：默认只读取当前主 skill 和最多一层直接 reference；只有命中明确 gate
时才路由 specialist skill。跨 skill 的关系是职责路由，不复制完整流程，也不递归串联。

当前高频 gate：

- `agent-doc-hygiene`：治理 agent-facing 文档。scope 分为 `global`、`project`、
  `project + exit-gate`；`engineering-exit` 只使用受限的 `project + exit-gate`。
- `doc-arch-review`：评审 architecture、ADR、OKF、doc-root taxonomy 和 durable docs；
  不负责普通入口文档瘦身。
- `release preflight`：由 `engineering-exit` 在 MR 前执行，只做发布质量前置检查；
  最终 `release::candidate`、release YAML、`gray_steps` / `full_steps` / `deploy_plan`
  仍归 arch-hub release workflow。
- `coding-conventions`：维护工程执行约定和 `gitlab.flow` 等级语义；不接管项目推进状态。

`gitlab.flow` 当前用于区分工程收束强度：

- `l1`：严格工程项目；需要分支、MR 和 release 质量 gate，发布影响未知会阻塞。
- `l2`：过渡工程项目；需要分支、MR 和 release 风险提示，非关键风险可由用户确认放行。
- `l3`：个人 / no GitLab settings lint；用户确认 commit & push 后可按当前 scope 执行，
  不默认要求 release 兼容。

## Relationships

- [Architecture index](./index.md)
- [Vertical agent ll](./vertical-agent-ll.md)
- [Source-of-truth boundaries](./source-of-truth-boundaries.md)

## Decisions / Invariants

- release preflight 是 MR 前准备，不替代 arch-hub 的最终 `release::candidate` 流程。
- release 兼容性是运行态发布质量，不等于默认保留旧 API / CLI / 配置入口。
- `l3` 不默认要求 release 兼容；`l1/l2` 需要分支、MR 和 release preflight。
- specialist gate 的跨域发现默认记录为 follow-up，除非它阻塞当前 scope。

## Change Guidance

改 gate 或工程收束等级时，先检查：

- `gitlab.flow` 语义是否仍为 `l1|l2|l3`。
- `coding-conventions`、`engineering-exit`、`load-context` 和 `tool-routes` 是否一致。
- `l3` 是否仍允许用户确认后按当前 scope 直接 commit & push。
- `l1/l2` 是否仍通过分支、MR 和 release preflight 收束。
- 是否把 arch-hub release workflow 的最终发布编排复制进 `engineering-exit`。
