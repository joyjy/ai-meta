---
description: 工程收尾：收束源码、文档生命周期、review gates 和 MR 提审材料
disable-model-invocation: true
---

request = $ARGUMENTS

使用 `engineering-exit` skill 执行完整工作流。

Source of truth:
`~/.ai/skills/engineering-exit/SKILL.md`

执行要求：
- 将 `$ARGUMENTS` 作为本次工程收尾、准备提审或开 MR 前收束的补充输入
- 不在本 command 文件中复制源码检查、文档生命周期、review gates 或 MR 模板流程
- Git 动作按 `engineering-exit` 的 Git Exit Authority 与全局规则执行
- 若本文件与 skill 冲突，以 skill 为准，并优先修正本文件保持薄入口
