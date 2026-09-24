# MR Package

Use this reference when preparing the review package after source and doc gates.

## MR Description

MR descriptions default to Chinese. Keep commands, paths, API names, conventional
commit titles, and project-required section labels in their native form, but
write the explanatory body in Chinese unless the project explicitly requires
English. If a repo already has a GitLab / GitHub MR template, preserve its
section structure and fill the body in Chinese by default. On GitLab, the
entire human-authored package belongs under the exact `## User Description`
heading. The shared `gitlab-mr` helper adds or normalizes that heading and keeps
Managed PR Agent PR Agent content outside the protected section.

以下为无项目模板时的候选段落；只保留与本次变更相关的部分，GitLab 的保护 heading 始终保留。

```markdown
## User Description

## 变更摘要
- <改了什么>
- <为什么改>

## 验证
- <验证结论和关键证据；必要时附最小可复现命令>

## 文档
- <架构 / 文档 / ADR 生命周期变化>

## 风险 / 兼容性
- <发布运行态兼容、迁移、回滚或高风险说明；不要用泛泛“兼容旧逻辑”替代具体发布风险>

## 发布预检
- gitlab.flow: <l1|l2|l3|unknown>
- <l1/l2 时记录验证证据、灰度新旧 pod 并存、配置/依赖/数据/MQ/网络/缓存/回滚影响；l3 或不适用时说明跳过原因>

## 未包含 / 后续
- <保留或来源不明的 dirty paths、保留原因、下一步、延后计划项、跳过的检查>
```

## Title

Prefer concise titles:

- `docs(<area>): <target-state change>`
- `feat(<area>): <user-facing capability>`
- `fix(<area>): <bug fixed>`
- `chore(<area>): <tooling or workflow change>`

Avoid titles that describe the plan artifact rather than the final change.

## Commit Split

Suggest a split only when it improves review:

- Source behavior and tests.
- Durable docs / ADR.
- Agent instructions / skills / workflow metadata.

Do not split just to make small commits if the reviewer would need to read them
together anyway.

## Confirmation

执行前核对 exact scope、flow 和用户已有授权。按入口的 Git Exit Authority 判断 push 与 MR/PR 写入权限及用户限制。先完成可审阅的 scope、验证证据和 MR 草稿，再执行已授权动作，不重复请求已有授权。用户限制为本地收尾时报告待推送状态。

When executing authorized Git actions, include current scope, separately
committed concerns, preserved / unknown dirty paths, verification evidence, and
the `gitlab.flow` result in the closeout report before or alongside the action
result.

## Verification Style

验证段写“结论 + 能支撑结论的证据”，不要写验证工具流水账。

- 不列举工具本身作为内容，例如只写 `spotless`、`sonarlint`、`compileJava`
  这类名称没有额外审阅价值。
- 命令只在能帮助 reviewer 复现、定位风险或解释覆盖范围时保留；否则合并成一句
  “本地格式检查、编译和目标单测通过”。
- CI 已经能直接看到的常规 pipeline job 不需要逐项抄回 MR 描述；写
  “CI pipeline passed” 或“等待 CI 验证”即可。
- 失败、跳过或无法本地验证的项必须保留原因和替代证据；不要为了压缩而省略风险。
- 对行为变更优先写验收结果，例如“容器内 `pytest` 5 条 account-region smoke 通过”，
  而不是列完整命令矩阵。

## Post-write Readback And CI Boundary

MR/PR 创建或更新后，回读刚写入的 exact 对象一次，确认实际 source branch、target branch、HEAD SHA 和 description 保护段。不要因附近存在旧 MR/PR 而重新分析或修改它；写后结果 ambiguous 时也不要盲目重试写操作。

随后，若项目存在适用 CI，查询一次绑定当前 HEAD 的 run/pipeline；无 CI 则记录 not applicable。若 run/pipeline 尚未物化，只允许一次短时 bounded retry 来确认 attachment。仍不可见时保留 exact MR/PR、HEAD、attachment 缺口和后续 oracle，不将其记为交付验收通过。

当前任务的 CI 等待、异步结果接续与暂停边界统一遵循 `~/.ai/instructions.md` 的「异步执行与结果收口」。已绑定 run/pipeline 时保留 ID、URL、HEAD 和状态；pending/running 按该规则安排接续，terminal 结果核对 source/revision 后按本次 acceptance 收口。MR 写入成功、CI attachment 成功和交付验收通过分别判断；本 reference 不另设等待授权门槛。
