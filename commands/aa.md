---
description: 显式运行 agent-assignment 执行分流
disable-model-invocation: true
---

input = $ARGUMENTS

读取并执行 source-of-truth skill：
`~/.ai/skills/agent-assignment/SKILL.md`

将 `$ARGUMENTS` 作为任务补充；为空时使用当前任务。不要在此复制分流规则。
