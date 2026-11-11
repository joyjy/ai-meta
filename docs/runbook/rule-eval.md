---
type: Runbook
title: rule-eval 盲测
description: 用冻结场景比较规则文本或模型配置的新旧版本，作为改动项自动落地的验收。
tags: [ai-meta, rule-eval, rollerskate, skill-verification]
---

# rule-eval 盲测

`~/.ai/scripts/rule-eval` 把冻结的决策场景交给多个 agent 作答。每个 agent 分别使用基线版和候选版规则，结果按 spec 中预先写定的答案判定。daily-review 的「改动项的验证与落地」和 Skill Verification Trace 的「RS 实验」都使用它。本文件是 spec 格式、判定规则和目录的唯一来源。

## 目录

每个 owner 一个目录，位于 `~/.ai/rule-evals/<spec id>/`。它是本机私有状态，不进 git。

```text
<spec id>/
├── spec.json
├── rules/                  # 基线和候选规则文本
├── scenarios/<场景 id>/CONTEXT.md
└── runs/<UTC 时间戳>/      # start 生成：spec 快照、每组 workspace 与 intent、run.json、result.json
```

场景长期保留。之后再修改同一 owner 时，沿用已有场景，并按需补充新场景；已有场景退化即判为 `fail`。

## spec.json

```json
{
  "schema": "rule-eval.spec.v1",
  "id": "daily-review",
  "owner": "<exact 规则文件或配置路径>",
  "arms": {"baseline": "rules/baseline.md", "candidate": "rules/candidate.md"},
  "agents": [
    {"id": "codex", "ref": "agent:codex", "model": "gpt-6-astra", "effort": "medium", "target": true},
    {"id": "claude", "ref": "agent:claude"},
    {"id": "pids", "ref": "agent:pi-ds"}
  ],
  "samples": 2,
  "timeout_seconds": 3600,
  "scenarios": [{"id": "receipt", "choices": ["A", "B", "C", "D"], "expected": "C", "holdout": false}]
}
```

- `id`、agent id 和场景 id 不能含下划线，因为节点 ID 用下划线拼接。
- `target` agent 恰好一个，取 owner 实际运行时的模型和推理强度。其他 agent 只用来观察稳健性。
- 比较模型配置时，两组使用同一规则文件，并写成 `{"rule": "...", "effort": "medium"}`。`model`、`effort` 只覆盖 target agent。
- 至少 1 个场景的 `holdout` 为 true，即不来自改动草案取材的案例。
- 场景数 × agent 数 × `samples` + 1 不超过 64，这是 RS DAG 的节点上限。

## CONTEXT.md

- 只写关键选择点之前的信息：用户请求、当时的事实和工具输出。删去之后的用户纠正，去掉凭据和个人信息。场景会发给非本机模型。
- 末尾写一个问题和 2–4 个带字母的选项。预期答案只写在 spec 里，不写进 CONTEXT.md。正确选项的字母位置在各场景间打散。

## 命令

- `rule-eval start <spec.json> [--dry-run]`：为每组建一个只含 `TASK.md`、`RULE.md` 和场景的 Git workspace，再启动一个只读 DAG Run。节点看不到另一组的规则，也看不到预期答案。`--dry-run` 只建 workspace 并运行 `rs run validate`。
- `rule-eval collect <run 目录> [--no-cancel]`：读取两组 Run 的节点结果并判定。节点都结束后，如果 Run 仍未到终态（例如停在 needs_human），collect 会取消这两个实验 Run；`--no-cancel` 保留它们。
- `rule-eval usage`：本地调用统计。

输出是供分析的 JSON（`rule-eval.run.v1`、`rule-eval.result.v1`），失败时 stderr 输出错误类别。spec 错误退出 2，RS 或文件错误退出 1。

## 判定

`collect` 输出 `verdict`：

- `pending`：还有场景节点没结束。
- `inconclusive`：target agent 有节点失败或没有给出有效选项。
- `no_change`：两组在 target agent 的每个节点都选对。改动没有可测收益，不落地。
- `pass`：候选版在 target agent 的每个节点都选对，基线版至少错一个，并且每个 agent 在候选版下的正确数都不低于基线版。只比较两组都有效的节点。
- `split`：target agent 的条件与 `pass` 相同，但至少一个其他 agent 在候选版下的正确数低于基线版。改动只适合部分 agent，`reasons` 列出退化的 agent。`split` 不是 `pass`，不落地。
- `fail`：其余情况，`reasons` 列出选错的节点或退化的 agent。

## 边界

- 一个场景只测一个选择点，不代表长上下文中的真实表现。`pass` 只说明在冻结输入下选得对。
- Skill Verification Trace 的「RS 实验」只把 `pass` 记为通过，`split` 按未通过记录。
- 节点启动时是否加载全局 `instructions.md`，取决于 agent。2026-11-09 的探针 `~/.ai/rule-evals/isolation-probe` 显示：`agent:codex` 和 `agent:pi-ds` 会加载，`agent:claude` 以 `--safe-mode` 启动，不加载。
- 测 skill、reference 或 tool-route 文本时，两组都带着同一份全局规则，与真实运行一致。claude 节点比真实运行少一层全局规则。
- 测 `instructions.md` 本身时，codex 和 pids 的两组都带着当前版全文，结果无效。只有 claude 节点的结果可用。
- 规则文本以文件形式放进 workspace，所以只证明内容差异，不证明客户端发现并加载了 skill。
- RS DAG 没有汇总节点：一个节点失败会阻塞结果节点，所以 collect 直接读取每个节点。
