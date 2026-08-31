---
description: 接入、校验或维护 coding-conventions 编码约定与工程 pattern
---

request = $ARGUMENTS

使用 `coding-conventions` skill 执行完整工作流。

Source of truth:
`~/.ai/skills/coding-conventions/SKILL.md`

执行要求：
- 将 `$ARGUMENTS` 作为本次初始化、查询、更新编码约定或维护工程 pattern 的补充输入
- 不在本 command 文件中复制初始化、校验、模板选择、Pitfall、pattern 或 include 加载规则
- 若本文件与 skill 冲突，以 skill 为准，并优先修正本文件保持薄入口
