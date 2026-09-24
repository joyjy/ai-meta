# Dirty Closeout: Separate Ready Concerns

仅在完整 dirty inventory 出现 `separate-ready` 时读取。它仍属于当前已解析 repo 的 closeout，不授权扩扫其他 repo。

- 先确认额外 concern 的 owner、scope、验证证据，以及可与当前交付独立解释的 commit 边界；同文件按 hunk 区分，无法安全分离则保留并说明。
- `l3`：默认一并验证并按 concern 组织 commit；需要远端动作时沿用显式 `ee` authority 与当前 branch/MR 规则，不强塞进一个 commit。
- `l1/l2`：查明 branch、target 与已有 MR。符合现有 MR 目标则更新，否则使用独立 topic branch 和新 MR；无法确认目标时点名缺口，不猜测或仅说已跳过。
- `l2`：通过适用验证、评审和 release gates 后，按 `ee` authority 直接 commit、push、创建或更新 MR，并报告各自范围与链接。
- `l1`：先形成可审阅 diff、验证证据和具体 MR 去向，再确认额外 concern 的 commit/push/MR；已有明确授权不重复询问。当前任务仍按主入口的 Git Exit Authority 执行。
- 显式 scope 限制优先；`preserve/unknown` 不进入交付。
