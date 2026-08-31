# loop-ledger-and-context-closeout

仅在 engineering-exit 发现当前项目 loop-ledger artifact，或当前 route 包含 exact context-backed final-form 时读取。

loop-ledger-bound 状态映射：本地已验证但禁止提交为 `commit_ready`；远端 package 已准备但缺授权为 `remote_write_ready`；需要新 work order 为 `next_ff_ready`；工具/证据阻塞为 `blocked`；只缺一个人类决定为 `needs_human`。状态本身不新增 git 或远端授权。

## loop-ledger-artifacts

- `~/.ai/loop/` 是 active area，没有 `active/` 子目录。检查新 `*.ll` segmented ledger，以及 legacy `*.json` 和匹配的 `.feedback.jsonl`。
- 只选择通过 cwd、repo path、contract target、modified paths、task title，或当前 session/dispatch/WorkItem/handoff 的 exact contract path 明确属于当前项目的 artifact。仅可能相关的条目报告为 `possible related`，不得移动。
- 新 ledger 先运行 `~/.ai/scripts/verify-ll-contract <exact-path>`，再用 `~/.ai/scripts/ll-ledger tail <exact-path>` 查看相关 appended events。Engineering-exit 只在 closeout 报告中 hand off exact ledger path 和 route，不读取 audit worker、不 dispatch，也不创建 receipt；audit 不是本次 exit gate。
- `/ll` 只记录终态，不移动文件。Engineering-exit 负责 exact ledger 匹配、验证和 handoff；`save-context` 是唯一自动 audit dispatch owner，显式 audit follow-up 是不执行 save 时的补位入口。
- Engineering-exit 不归档 ledger；保留 exact active path，后续 `save-context` 或显式 audit follow-up 在 audit settlement/discard 后再归档 receipt 绑定的 exact ledger。
- `needs_human` / `blocked` / `active`：保持 active 并报告原因。
- 当前任务 feedback 仍按 effective contract 处理；需要新工作时产生 concrete final-form 并把 loop-ledger exit 映射为 `next_ff_ready`，不得自动执行。独立 audit candidate 只在后续 settlement 路由，不重新打开已完成实现。
- 普通 closeout 不删除 loop-ledger artifact；completed retention cleanup 需要独立明确请求。

## Exact Context-Backed final-form

- 只有在当前 exit 已完成 final-form 的 goal、acceptance、required checks，以及本次授权包含的 commit/push/MR 动作后才清理。blocked、needs_human 或 partial 不算完成；prepare-only 只有在 final-form 本身以 prepared state 为目标时才算完成。
- 只处理当前 project 的 selected mainline/workstream route，且 embedded final-form 的 exact goal/scope 与本次工作匹配。运行 `~/.ai/scripts/context-ff-merge <abbr[:workstream]> --clear-completed --expect-goal '<exact ff.goal>'`；goal 缺失或不匹配必须停止。
- route 仍有 Doing/Blocked 时只清 final-form。final-form-only workstream 清空后移除该 workstream 和 exact Markdown detail；mainline 为空时标为 idle。
- 本轮产生 executable follow-up 时，用新 final-form 替换完成项并保持 route active；不要把完成 final-form 当执行历史保留。
- closeout 报告必须点名 cleared route；不得修改 sibling route、GTD/issue history 或普通 Next Step。
