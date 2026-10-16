# Git worktree 生命周期

- worktree 放在主项目目录旁，使用 `<repo>-wt-<purpose>` 命名。
- 创建后立即在项目 context 的 `Critical Context` 登记。登记 exact path、branch、purpose 和 cleanup condition。
- 未完成登记时，禁止继续任务。
- 删除后同步移除登记。删除前遵守全局规则的确认边界。
- 任务结束时，清理没有后续用途的 worktree。仍有用途时保留登记和清理条件。
