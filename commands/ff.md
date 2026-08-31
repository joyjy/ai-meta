---
description: 将当前需求或下一步收束成 final-form 可执行规格
---

input = $ARGUMENTS

读取下列 source-of-truth skill 文件，并按其中定义执行完整工作流。

Source of truth:
`~/.ai/skills/final-form/SKILL.md`

执行要求：
- 将 `$ARGUMENTS` 作为需求补充；若为空，使用当前对话和已加载 context
- 不在本 command 文件中复制 schema、context 合并、`grill` 路由、澄清或分发规则
- 若本文件与 source-of-truth 文件冲突，以 source-of-truth 文件为准，并优先修正本文件保持薄入口
