---
description: review-router：按评审对象选择 strategy，输出 findings 与 next-review 决定
---

input = $ARGUMENTS

读取并执行 source-of-truth skill：
`~/.ai/skills/review-router/SKILL.md`

将 `$ARGUMENTS` 作为任务补充；为空时使用当前对话和已加载 context。不在本文件复制 skill 流程；与 skill 冲突时以 skill 为准，并修正本文件。
