---
description: 编译 runtime-neutral ll contract 并分发到目标执行入口
disable-model-invocation: true
---

input = $ARGUMENTS

读取下列 source-of-truth skill，并按其中定义执行工作流。

Source of truth:
- `~/.ai/skills/loop-ledger/SKILL.md`

执行要求：
- 将 `$ARGUMENTS` 作为输入，读取 source-of-truth 文件并按其中定义执行完整工作流
- 不在本 command 文件中复制或追加 architecture、verifier、contract 编译、checkpoint、反馈记录、git flow 或输出格式
- 若本文件与 source-of-truth 文件冲突，以 source-of-truth 文件为准，并优先修正本文件保持薄入口
