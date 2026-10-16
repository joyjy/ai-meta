# Pitfall Maintenance

只在新增、晋升、更新或清理工程 pitfall 时读取。Pitfall 记录看似合理但高概率导致错误的工程做法，不承载 agent 工具路线摩擦或完整事故复盘。

## Placement

1. 跨项目默认成立的长期规则优先写入 `../templates/general/AGENTS.md`；明显属于单一技术栈时写对应模板。
2. 表述包含“不要做什么”“为什么容易错”，必要时补推荐替代方式。
3. 一次性事故只留在项目任务或 `../preferences/pitfall-watch.md`。若短期内可能影响多个个人任务，并已有 signals、probe 与 verification，可晋升为带到期日的 `../preferences/temporary.md`。
4. Temporary pitfall 只进入个人默认层，可由同步器进入个人父级 `AGENTS.md`，但不注入具体团队项目；到期后失效并提示清理。
5. 默认工具 / 权限路线失败、sandbox fallback、skill 误路由和重复重试进入 `~/.ai/agent-frictions.md`，不进入 pitfall。

## Recurrence And Evidence

- “重复”按归一化 mechanism signature 判断，不靠 agent 记忆，也不把同一 session 的多次编辑或中断计为独立复现。
- 首次命中进入项目任务或 pitfall watch；同一 signature 在独立 session / project 第二次命中后，才评估 temporary；跨项目持续复现后再评估长期模板。
- 主入口按晋升条件读取 [证据分类](../../../docs/reference/evidence-classification.md)：真实事故、MR 或 probe 是 `KNOWN`，独立命中次数是 `COMPUTED`，跨项目可迁移性是带依据的 `INFERRED`。`COMMON`、`FRAME` 或 `GUESS` 不能单独支持晋升。
- 最终模板使用工程语言，不写内部证据标签；只保留可执行提醒和 evidence anchor。

已过期 temporary 条目不得继续作为工程结论。
