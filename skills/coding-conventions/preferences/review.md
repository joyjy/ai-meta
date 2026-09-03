# Review 个人偏好

这些偏好独立于团队模板维护；`sync-conventions.sh` 只会把本文件写入 `~/Documents/projects/AGENTS.md` 的 `general` 受控块，不注入具体项目 `AGENTS.md`。

- 做 review 时优先指出 bug、回归风险、缺测试和高风险边界；不要把审美、命名或低影响重排放在前面。
- 创建 PR/MR 或触发 Pipeline 后，把 exact HEAD 绑定到 source-owned CI oracle 并只回读一次；`pending / running` 时记录 pipeline identity、当前状态和需要人处理的事项后结束。terminal oracle binding 不等于当前任务同步等待；只有用户明确要求监控时，才使用独立监控机制，不阻塞当前任务。
- 收到他人 review 意见后，逐条处理或说明不采纳原因；有歧义时先让用户决定，不替用户做产品或团队取舍。
