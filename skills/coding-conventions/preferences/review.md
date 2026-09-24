# Review 个人偏好

这些偏好独立于团队模板维护；`sync-conventions.sh` 只会把本文件写入 `~/Documents/projects/AGENTS.md` 的 `general` 受控块，不注入具体项目 `AGENTS.md`。

- 做 review 时优先指出 bug、回归风险、缺测试和高风险边界；不要把审美、命名或低影响重排放在前面。
- PR/MR 与 Pipeline 的异步执行、结果接续和等待边界统一遵循 `~/.ai/instructions.md` 的「异步执行与结果收口」；写后身份与 CI 绑定核验使用 `engineering-exit/references/mr-template.md`。
- 收到他人 review 意见后，逐条处理或说明不采纳原因；有歧义时先让用户决定，不替用户做产品或团队取舍。
