---
name: engineering-exit
description: "engineering-exit / ee: 收束实现后的源码、文档、验证证据和 MR 准备。适用于用户说 ee、engineering exit、工程收尾、准备提审、开 MR 前收束、ship this change，或要求把 plan 转为终态 docs/ADR 后开 MR。"
disable-model-invocation: true
---

# engineering-exit

收束源码、文档、验证和 Git 交付；context 保存归 save-context。

## Git Exit Authority

显式 `ee` 授权按 flow 对下方交付 scope 执行 commit、push、创建/更新 MR/PR，不重复确认；`prepare-only` 不写 Git，`local-only` 仅本地，其他明确限制优先。gate 失败阻止对应写入。此授权不含破坏性清理、issue/label/release 状态变更、merge、force push 或远端历史改写。

从项目 `index.md` 核对 `gitlab.flow`：

- `l1`：非 default topic branch 交付；release-impact unknown 阻止远端写入，纯 post-merge unknown 留 exact action。
- `l2`：非 default topic branch 交付；非关键 release unknown 需用户接受风险。
- `l3`：当前分支交付；非 default branch 创建/更新 MR，default branch 无 MR。默认免 review-router/GitLab settings lint，用户或项目指定评审与其他 gates 仍执行。
- missing/unknown：本地 commit 遵循全局分支限制；远端只准备，待 flow 明确。

## Dirty Closeout

- 检查每个已解析目标 repo 的完整 dirty diff：`current-scope` 为当前任务；`separate-ready` 为可归因、已完成且可独立验证的其他改动；`preserve` 为 WIP、blocked、failed-check 或用户要求保留项；来源不明为 `unknown`。不能仅因非当前任务而跳过检查。
- 存在 `separate-ready` 时读取 `references/dirty-closeout.md`；没有时不加载。各 flow 均服从显式 scope 限制；`preserve/unknown` 给出原因与解除条件，不以清空工作区为验收目标。

## Conditional References

只加载命中 gate 的直接 reference；specialist 也由本入口路由，不继续向下串联：

- plan、durable docs、ADR 或 source comment 生命周期：`references/doc-lifecycle.md`。
- agent docs：直接运行 `../agent-doc-hygiene/SKILL.md`。
- architecture/source-map：直接运行 `../doc-arch-review/SKILL.md`。
- release preflight：`references/review-gates.md`。
- 风险、release、review 或外部事实混合证据等级：`references/evidence-classification.md`。
- 准备或更新 MR/PR package：`references/mr-template.md`。
- 存在 exact loop-ledger 或当前 route 的 context-backed final-form：`references/state-closeout.md`。
- 当前 scope 修复了 repo-maintenance finding：`../../../gtd/docs/architecture/repo-maintenance.md` 的「修复交付收尾」。

## Hard Gates

- 删除须先列 exact paths 并确认；已证明完成的 exact final-form recovery route 是唯一窄例外。
- 解释整个 dirty worktree。不得 revert、隐藏或提交未知、WIP、blocked 或 failed-check 修改。
- 探索中的架构、命名、source of truth 或 skill 行为不因 exit 获得写入授权。
- 移出 scope 的内容不留解释其缺席的残留；仅保留有当前证据的安全、兼容或外部契约边界。
- 历史 open ledger、旧 revision 样本缺口和任务前已有的验证债默认是 advisory：报告 exact record 与 oracle。项目发布门禁要求，或当前任务修改了对应行为且验收需要时，执行与本次交付直接对应的最窄验证；验证证据服务当前 readiness，ledger verdict 随真实证据更新。

## Workflow

1. **Resolve scope**：核对 roots、当前/default/target branch、平台、flow 和 plan；按 Dirty Closeout 确定交付 scope。同文件按 hunk 区分 concern，无法分离则保留并说明。首次 push 或已有 MR 时 fetch target、检查分叉；rebase 前保护保留的 dirty。
2. **Verify implementation**：按项目适用的 coding-conventions walkthrough 完整交付 diff（交付基线后的提交及本次 dirty），只补读当前技术栈模板。范围内遗漏直接修正，超出 scope 的结构调整报告；编译和 lint 不能替代 walkthrough。复用当前 revision 的证据，补齐项目必需 checks 与最窄 acceptance；新改动、失败或未解决风险触发扩大验证。缺口说明依赖与替代证据。
3. **Review**：`l1/l2/unknown` 读取 `../review-router/SKILL.md`，以 `caller=engineering-exit` 从 simple 开始，最多升级一次；`l3` 仅执行用户或项目指定评审。修复 blocking findings 并重跑相关检查；非阻塞扩展记录 follow-up。
4. **Sync docs**：行为、契约、runtime 或入口变化同步 owner；结构变化检查 source map。按 Conditional References 执行命中的 docs gates，不扩为全仓审计。
5. **Prepare delivery**：`l1/l2` 或 release-ready 请求执行 preflight；准备 MR 时校验 `mr-template.md` headings。仅对当前项目 exact ledger/final-form 按 `state-closeout.md` 收口，报告 ledger path，不派发 audit。
6. **Git exit**：复核 staged scope、branch、flow、checks 和 target freshness，按上述 authority 提交交付。MR 写后按 `mr-template.md` 回读 identity、保护段、CI attachment 并遵循等待边界。
7. **Settle findings**：scope 对应的维护 finding 已验证并 commit 后，主动按 GTD「修复交付收尾」结算；缺少 exact binding、commit 或证据则报告原因，不把部分修复标为完成。

## Exit Criteria

- dirty 全部按 Dirty Closeout 结算，未交付项有具体原因、解除条件和下一步。
- checks/review/docs/release/MR gates 有结论和证据；skipped 明确原因与替代证据。durable docs 与交付行为一致，state closeout 只处理 exact match。
- Git 写入只含已验证交付 scope；HEAD 相对 target 的 freshness 已证明，远端动作不超授权。

## Output

先给终态，仅展开影响交付的 checks、dirty、gates、MR、风险与动作。
