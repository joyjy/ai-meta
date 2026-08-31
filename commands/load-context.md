---
description: 从 ~/.ai/contexts/<abbr>.md 加载主线或内嵌分线 context，快速恢复 session 工作状态
disable-model-invocation: true
---

abbr = $ARGUMENTS

读取下列 source-of-truth skill 文件，并按其中定义执行完整工作流。

Source of truth:
`~/.ai/skills/load-context/SKILL.md`

执行要求：
- 将 `$ARGUMENTS` 作为 abbr 输入；若为空，由 source-of-truth 文件按自身规则从当前目录 `index.md` 读取
- 不在本 command 文件中复制加载流程、分线规则或输出格式
- 若本文件与 source-of-truth 文件冲突，以 source-of-truth 文件为准，并优先修正本文件保持薄入口
