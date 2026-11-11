# Git 分支扫描与确认清理

定时任务调用 `scripts/amt-git-refresh`。定时扫描使用 dry-run。
扫描会刷新远端引用。原有刷新逻辑仍会快进干净的当前分支。

## 扫描结果

默认报告位于 `~/.ai/amt/runtime/git-refresh.json`。
同目录的 `git-refresh.review.md` 供人阅读。
JSON 的 `review_snapshot` 指向按 fingerprint 保存的快照。
后续扫描保留旧快照，清理时使用确认过的快照。

| 分类 | 证据和处理 |
| --- | --- |
| `redundant` | 分支已包含在默认分支中，或原 squash 校验与默认分支可达性均通过。列为清理候选。 |
| `possibly_replaced` | 分支改动过的文件已与默认分支一致，或 patch 全部等价。复核内容后决定。 |
| `unique_content` | 仍有未匹配的改动。报告列出提交、文件和依赖清单 diff。 |
| `retain` | 分支已检出、MR 开放，或远端分支受保护。保留。 |
| `insufficient_evidence` | 缺少默认分支或读取失败。补齐证据后重扫。 |

提交不同不代表功能缺失。依赖版本被替代、业务方案被废弃，需要内容判断。
文件和提交清单是证据，不是工具对业务等价性的裁决。
每个提交清单最多显示 100 个条目。依赖 diff 最多显示 8000 个字符。
报告会标明截断。

扫描通过 `wt-sweep list` 单独盘点 worktree。
worktree 的删除规则由 `coding-conventions/references/worktree-lifecycle.md` 持有。
分支清理入口不会删除 worktree。

`review.attention_required` 表示证据发生变化。
报告记录新增、变化和消失的 entry_id。
证据未变化时，脚本只输出无需关注的摘要。
本入口不负责消息投递。

## 确认与触发

前置条件：读完候选内容，并确认具体条目和删除范围。
`entry_id` 绑定仓库、分支、本地 SHA 和远端 SHA。

1. 从报告取出快照路径和条目 ID。
2. 预览指定条目的清理动作。

```sh
~/.ai/scripts/amt-git-refresh \
  --apply-review /absolute/path/to/snapshot.json \
  --select ENTRY_ID \
  --scope both
```

`--scope` 可选 `local`、`remote`、`both`。
重复 `--select` 可选择多个条目。
预览会刷新引用并检查远端状态。
预览保留所有分支。

3. 为同一命令添加 `--confirm`。

如果条目属于 `possibly_replaced` 或 `unique_content`，还需添加 `--discard-unmerged`。
这个参数表示明确放弃已审阅的独有内容。
agent 必须先取得用户对具体条目的删除确认。

用户也可以在对话里确认具体条目。
agent 读取原快照，再使用同一个执行入口。
每轮新增条目都需要确认，历史清理许可不扩大到新条目。

## 执行检查与回执

执行前检查整批选项。
仓库身份、分支 SHA 或默认分支变化时，命令拒绝执行。
存在开放 MR、受保护分支或 worktree 占用时，命令拒绝执行。
执行检查直接读取 GitLab，绕过扫描读取缓存。

远端删除使用精确 SHA lease。
本地删除使用 `update-ref` 的旧 SHA 条件。
扫描后新增的提交会导致删除失败。
`both` 先删除远端，再删除本地。

每个删除动作后回读引用。
清理回执默认写到快照旁的独立时间戳文件。
也可用 `--output` 指定回执路径。

命令逐项保存动作状态。中断或超时可能留下 `attempting` 或 `unknown`。
恢复前先回读引用，禁止把受理当成删除成功。
批量删除可能部分成功，剩余内容需要重扫。

`amt-git-refresh usage` 输出本地调用统计。
统计只记录命令名、时间、耗时和退出码。
