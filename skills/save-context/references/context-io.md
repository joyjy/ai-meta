# save-context: compatibility and special I/O

仅在非 Codex client、legacy 调用或需要特殊 flags 时读取。所有 filesystem writes 仍只经 `~/.ai/scripts/save-context`。

## Client I/O

- Codex Desktop 使用主 skill 的 `--orchestrate` + `--context-file` 路径；长 YAML 不走 interactive stdin。
- 其他 client 能安全提供 stdin 时可用 `--context-stdin`。只能 pipe stdin 时可用 `--context-file -`。
- Legacy 非 orchestrator 调用保留原 `save_context.py` 参数、输出与 exit codes；不要把它当 Codex 默认入口。

## Special Flags

- `--validate-only`：以同一输入执行只读 compile/validation，包括确定性 timeline 日期，不写 context 或 Daily Note。
- `--allow-empty`：仅在明确要清空 snapshot 时使用；默认拒绝空白输入。
- `--date YYYY-MM-DD`：timeline 属于非当前本地日期时使用。
- `--skip-timeline` 或省略 `--timeline`：没有 substantive Daily Note 时使用。
- `--timeline-only --timeline "[...] ..."`：只有 work-log 价值时使用，并省略 context input；admission 仍必须先执行。
- Confirmed workstream closure 应重写项目 context 移除该 route；不要用 `--delete-context` 删除 context.v3 中的单个 workstream。

## Validation And Receipt

Admission 先运行，然后执行只读 context compile/validation preflight，再写 context/timeline。Preflight 或正式写入失败保留 helper 的非零 exit 并停止后续 stage；非空输入经校验后才 atomic replace。Orchestrator 只发出一个 `save-context.checkpoint.v1` receipt，native title 仅在 receipt 证明 context stage 成功后更新。
