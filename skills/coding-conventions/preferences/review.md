# Review 个人偏好

这些偏好独立于团队模板维护；`sync-conventions.sh` 只会把本文件写入 `~/Documents/projects/AGENTS.md` 的 `general` 受控块，不注入具体项目 `AGENTS.md`。

- 做 review 时优先指出 bug、回归风险、缺测试和高风险边界；不要把审美、命名或低影响重排放在前面。
- 创建 PR/MR 或触发 Pipeline 后，只回报链接、当前状态和需要人处理的事项；agent 不在当前任务中等待或轮询 CI。只有用户明确要求监控时，才使用独立的监控机制，不阻塞当前任务。
- 收到他人 review 意见后，逐条处理或说明不采纳原因；有歧义时先让用户决定，不替用户做产品或团队取舍。
