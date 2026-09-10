---
type: Reference
title: Skill verification trace
description: Skill 改动从 revision identity 到真实行为样本的本机验证闭环。
resource:
tags: [ai-meta, skill, verification, runtime]
---

# Skill Verification Trace

## Scope

本机制回答一个窄问题：某次 skill 改动是否已被目标客户端加载，并在之后的真实样本中满足事先声明的验收条件。它不替代 skill 测试、代码评审、日志系统或任务恢复 context。

## Ownership And Storage

- `scripts/skill_verification.py` 拥有 `skill.verification.v1` schema、source identity、事件写入和 verdict 计算；`scripts/skill-verification` 是跨客户端薄入口。
- `install.sh` 将两个入口发布到 `~/.ai/scripts/`。
- `~/.ai/skill-verification/changes/<change_id>.json` 保存本机逐次验证记录，不进入 Git，也不反向成为 skill source of truth。
- `change_id` 由 canonical `SKILL.md` path、source fingerprint、变更摘要、验收条件和所需样本数确定；`begin --artifact <path>` 可把直接行为 reference 纳入同一个 source fingerprint。dirty worktree 使用 `working-tree:<HEAD>:<digest>` revision identity，避免把未提交内容冒充 commit。

## Evidence Lifecycle

```text
begin(change contract + fingerprint)
  → check(static evidence)
  → load(client/session + matching content fingerprint)
  → sample(post-load behavior evidence)
  → status(verdict)
```

- `begin` 在改动完成前登记 canonical path、revision identity、摘要、验收条件和 `required_samples`。
- `check` 记录测试、lint 或人工静态审查的引用；同名 check 以最新事件为准。
- `load` 核对 `SKILL.md` 及该 change 登记的全部 artifact 的 SHA-256，完全匹配才生成 `load_id`。调用方仍须提供真实客户端加载证据；磁盘内容匹配、仅阅读源文件或改动前的历史调用不算加载回执。
- `sample` 必须引用匹配的 `load_id`。证据只存可回读引用和短注释，不复制完整对话、prompt 或敏感正文。
- `status` 是自动化的只读入口；自动化不得直接猜测、补写或修改 ledger。

## Verdict Contract

- `pending`：尚无静态检查，或行为变更还没有 post-load 样本。
- `static_validated`：所有最新静态检查通过，且该变更显式声明不需要行为样本；它不等于真实行为已验证。
- `inconclusive`：已有 post-load 样本，但通过样本尚未达到声明数量。
- `validated`：静态检查均通过，且匹配目标 fingerprint 的 post-load 通过样本达到声明数量。
- `falsified`：最新静态检查失败，或任何匹配版本的 post-load 样本失败。修复后的新内容形成新的 `change_id`；不得用重写历史抹掉失败证据。

## Daily Review Integration

`amt:daily-review` 每轮最多调用一次 `~/.ai/scripts/skill-verification status --limit 20`，按 `change_id` 与上轮 memory 比较状态变化。报告须区分 `static_validated` 与 `validated`，并把 `pending` / `inconclusive` 留作待采样项；它只消费 CLI 返回的结构化摘要，不扫描原始记录。

## Change Guidance

- 修改 schema、identity 或 verdict 时，同时更新本文件、`source-map.md` 和 `scripts/test_skill_verification.py`。
- 新增行为证据类型时，必须仍绑定 matching load fingerprint；不能用时间接近、文件路径相同或测试通过推断客户端已加载。
- ledger 不授予 restart、远端写入、通知或其他副作用权限。
