---
type: Reference
title: Skill verification trace
description: Skill 改动从 revision identity 到静态检查或实验证据的本机验证记录。
resource:
tags: [ai-meta, skill, verification, runtime]
---

# Skill Verification Trace

## Scope

本机制回答一个窄问题：某次 skill 改动的验收条件是否有静态检查或实验证据。个人使用积累不到足够的真实样本，所以真实样本是可选证据，不是完成条件。它不替代 skill 测试、代码评审、日志系统或任务恢复 context。

## Ownership And Storage

- `scripts/skill_verification.py` 拥有 `skill.verification.v1` schema、source identity、事件写入和 verdict 计算；`scripts/skill-verification` 是跨客户端薄入口。
- `install.sh` 将两个入口发布到 `~/.ai/scripts/`。
- `~/.ai/skill-verification/changes/<change_id>.json` 保存本机逐次验证记录，不进入 Git，也不反向成为 skill source of truth。
- `change_id` 由 canonical `SKILL.md` path、source fingerprint、变更摘要、验收条件和所需样本数确定；`begin --artifact <path>` 可把直接行为 reference 纳入同一个 source fingerprint。dirty worktree 使用 `working-tree:<HEAD>:<digest>` revision identity，避免把未提交内容冒充 commit。

## Evidence Lifecycle

```text
begin(change contract + fingerprint)
  → check(static evidence or RS experiment)
  → status(verdict)

optional: load(client/session + matching content fingerprint)
  → sample(post-load behavior evidence)
```

- `begin` 在改动完成前登记 canonical path、revision identity、摘要和验收条件。`required_samples` 默认 0，只在主动收集真实样本时声明。
- `check` 记录测试、lint、人工静态审查或 RS 实验的引用；同名 check 以最新事件为准。
- `load` 核对 `SKILL.md` 及该 change 登记的全部 artifact 的 SHA-256，完全匹配才生成 `load_id`。调用方仍须提供真实客户端加载证据；磁盘内容匹配、仅阅读源文件或改动前的历史调用不算加载回执。
- `sample` 必须引用匹配的 `load_id`。证据只存可回读引用和短注释，不复制完整对话、prompt 或敏感正文。
- `status` 是自动化的只读入口；自动化不得直接猜测、补写或修改 ledger。每条记录带 `source_drift`（登记后内容已变化的 artifact）与 `superseded_by`（同一 `SKILL.md` 更新登记的记录）。`status --open` 只列出 verdict 为 `pending`、没有更新登记且内容未漂移的记录。

## RS 实验

默认不跑实验。改动会改变 agent 判断，且做错有实际后果时，才跑一次。

- 在 push 前用最终 fingerprint 跑，不按每次编辑跑。
- 用同一组场景对比旧版和新版。已发布 skill 软链到工作区，所以旧版基线在编辑前跑，或把旧版放进 fixture。
- 评分规则在结果返回前写定。至少 1 个场景不取自本次规则的示例。
- 用 `check` 记录结果，`--evidence-ref` 写 Run ID 或结果文件。
- 执行入口是 `~/.ai/scripts/rule-eval`，spec 格式和判定规则见 [rule-eval runbook](../runbook/rule-eval.md)。
- 把规则文本放进 workspace 的实验只证明内容差异，不证明客户端发现和加载了 skill。

## Verdict Contract

- `pending`：尚无静态检查。
- `static_validated`：所有最新静态检查通过。这是默认完成状态，不等于真实行为已验证。声明了 `required_samples` 但样本未达数量的记录也判此状态。
- `validated`：静态检查均通过，且匹配目标 fingerprint 的 post-load 通过样本达到声明数量。
- `falsified`：最新静态检查失败，或任何匹配版本的 post-load 样本失败。修复后的新内容形成新的 `change_id`；不得用重写历史抹掉失败证据。

## Daily Review Integration

`skills/daily-review` 通过 `scripts/daily-review-collect` 的事实包消费 `status --open` 的记录，按 `change_id` 与上轮 memory 比较，只报告新出现的记录。报告须区分 `static_validated` 与 `validated`。它不追踪待采样项，不扫描原始记录，也不写 ledger。

## Change Guidance

- 修改 schema、identity 或 verdict 时，同时更新本文件、`source-map.md` 和 `scripts/test_skill_verification.py`。
- 新增行为证据类型时，必须仍绑定 matching load fingerprint；不能用时间接近、文件路径相同或测试通过推断客户端已加载。
- ledger 不授予 restart、远端写入、通知或其他副作用权限。
