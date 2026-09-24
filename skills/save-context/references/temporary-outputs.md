# save-context: temporary outputs

仅当本轮或选中 route 存在 agent 自建临时输出时读取。

- 盘点本轮创建与当前 route `Critical Context` 已登记的临时输出。仅为 `save-context` admission/context I/O 创建的一次性 payload 不登记，receipt 后按 exact path 清理。
- 无恢复价值的 agent 自建文件按 exact path 清理并从 context 移除；调用 `save-context` 授权这一窄类清理。worktree、他人文件、持久 artifact 和来源不明路径不在此例外内。
- 仍需跨回合复用的临时输出继续保留，并在选中 route 的 `Critical Context` 核对 exact path、purpose 和 cleanup condition；不复制输出正文。已清理的路径不再保留。
- 后续需要详单时读取登记的原文件，不重新查询或生成。
