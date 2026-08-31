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
- 选择 `ee` 默认就是授权工程收尾一口气完成 commit / push / open MR；除非
  `$ARGUMENTS` 明确限制为只准备、本地收尾、不提交、不 push 或不开 MR，否则按
  `engineering-exit` 的 privileged git exit 和 `gitlab.flow` 规则执行
- 若本文件与 skill 冲突，以 skill 为准，并优先修正本文件保持薄入口
