# save-context: route and closure

仅在 route 未知/歧义、新建 workstream 或判断 closure 时读取。普通已知 route 的 checkpoint 由主 skill 直接执行。

## Route

Context 是恢复快照，不是 durable knowledge。每个项目只维护 `~/.ai/contexts/<abbr>.md`；旧式 `~/.ai/contexts/<abbr>/<workstream>.md` 只兼容读取，不再创建。

- Mainline：供 `load-context <abbr>` 和 dashboard 使用的项目级恢复摘要。
- Workstream：有独立身份和具体未完成 Next Step，且不应覆盖 mainline 的项目内工作。
- Completed small task：结果已归位、没有独立恢复入口；不新建 workstream。

路由顺序：显式 `<abbr>` / `<abbr>:<workstream>` 优先；否则从当前 project `index.md` 取 `abbr` 并沿用明确的 existing workstream。仍未知或多个目标均合理时，只问一个会改变写入目标的问题。

- Bare `<abbr>` 写 mainline；显式 `<abbr>:<workstream>` 更新该 route，除非 closure 已确认。
- 不因文件多、话题多或完成了一个 slice 而拆 workstream。
- 只有用户命名，或任务具有稳定身份、具体未完成 Next Step 且写入 mainline 会混淆其他恢复状态时，才新建 workstream；名称用可读 slug，避免时间戳、近义重复和顶层别名。
- 项目 summary、handoff 或 promote 明确指向 mainline；completed small task 只同步 durable owner，并在有 work-log 价值时记 timeline。
- 更新 mainline 时保留无关 active workstream；更新 workstream 时 fixed writer 只合并该 route。

## Non-destructive Save

- 写前回读目标 context；repeat save 从既有 route、Doing、Blocked、Next Steps 与 Critical Context 开始。
- 只有 recovery/route/workstream state/closure/critical facts 变化，或用户要求 refresh 时重写；不要为了 timeline 覆盖 context。
- 不重复 timeline。跳过 context rewrite 时在最终 `临时状态层` 说明。
- 新建或修复结构时由主 skill 另选 schema reference；否则保留既有有效 schema。

## Closure

`save-context` 是正常 closure check；用户说“做完了 / 可以了 / 收束 / promote / 合到主线”也触发判断。

- Doing 已完成或为空、Next Step 为空或已迁入 durable owner/mainline/backlog，且重要结果已同步，才是 closure candidate。
- 有恢复价值但暂不继续时标为 `parked`；普通或歧义 workstream 不静默 close、promote 或删除。没有独立 Next Step 时建议 close，有具体 Next Step 时建议 keep。
- 普通 confirmed closure 先 durable sync，再从 YAML 和 Markdown detail 移除 route。
- 唯一窄例外：当前 session 直接证明 exact context-backed final-form 的 goal、acceptance、required checks 与 authorized exit actions 全部完成时，运行 `~/.ai/scripts/context-ff-merge <abbr[:workstream]> --clear-completed --expect-goal '<exact ff.goal>'`。helper 只清理 exact match；仍有 Doing/Blocked 时不会移除 route。不要把已清空 route 保留为 `idle` 或 `closure-candidate`，也不再请求第二次 closure 确认。
