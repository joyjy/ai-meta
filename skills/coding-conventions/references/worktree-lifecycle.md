# Git worktree 生命周期

- worktree 放在主项目目录旁，使用 `<repo>-wt-<purpose>` 命名。
- 创建后立即在项目 context 的 `Critical Context` 登记。登记 exact path、branch、purpose 和 cleanup condition。
- 未完成登记时，禁止继续任务。
- cleanup condition 写可观察的终态，例如 MR 合并或关闭、交付完成。用户确认是删除步骤，不能写成 cleanup condition。
- 任务结束时，用 `git worktree list` 对照该项目全部 route 的登记，并回读各 cleanup condition 的当前状态。未登记的 worktree 一并列出。
- cleanup condition 已满足时，先核验工作区 clean，且本地 HEAD 等于 MR 最终 head 或是其祖先。核验通过后，在本轮最终回复中列出 exact path、branch 和核验结果，请用户确认删除。禁止只登记为保留。
- cleanup condition 未满足或核验不通过时，保留 worktree，并在登记中写明原因。
- 用户确认后用 `git worktree remove <path>` 删除，不加 `--force`。squash 合并的分支用 `git branch -D` 删除。删除后同步移除登记。
