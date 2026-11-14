# Codex 模型表达规则

`plugins/route-context/hooks/codex-response-style.js` 是独立的 UserPromptSubmit hook。它只在输入的 `model` 精确等于 `gpt-6.1-sol`、`gpt-6-astra` 或 `gpt-6.1-terra` 时注入同目录 `codex-response-style.md`。其他模型、缺少模型字段或其他事件返回空结果。模型来自当前回合的 hook 输入。

规则要求汇报结果和具体缺口，并删除重复防误解的尾句。必要的风险、授权限制和证据缺口保留。这个 hook 只提供表达指导，实际回复质量需要真实会话验证。

## 安装与验证

将同目录 `codex-response-style-hooks.json` 合入 `~/.codex/hooks.json` 的 UserPromptSubmit 数组。将模板中的 `node` 替换为本机已验证的绝对路径，将 `${CLAUDE_PLUGIN_ROOT}` 替换为当前 checkout 的 `plugins/route-context` 绝对路径。保留已有 hook 的内容与顺序。这个独立定义仅在 Codex 用户层注册，Claude 的 settings hook 和插件默认 hook 清单保持原配置。

运行 `node --test plugins/route-context/scripts/test_codex_response_style.js`。再用精简 PATH 执行安装后的命令，分别传入目标模型和其他模型，核对注入与空结果。

在 Codex CLI 的 `/hooks` 中审核并信任新定义。真实验收需要目标模型回合出现 `response-style` 注入，并观察普通结果汇报和直接询问未完成状态两种回复。其他模型的新回合应无新增注入。此前状态为 `runtime_reload_ready`。在已注入的同一聊天中切换模型，历史上下文仍可能包含先前规则；需要隔离验证时使用新聊天。

停用时在 Codex hook 管理中禁用这一个定义。
