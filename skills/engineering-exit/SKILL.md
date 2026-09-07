---
name: engineering-exit
description: "engineering-exit / ee: 收束实现后的源码、文档、验证证据和 MR 准备。适用于用户说 ee、engineering exit、工程收尾、准备提审、开 MR 前收束、ship this change，或要求把 plan 转为终态 docs/ADR 后开 MR。"
disable-model-invocation: true
---

# engineering-exit

收束实现后的源码、文档、验证和 MR package；不用于设计、context 保存或简单修复。

## Git Exit Authority

用户选择 `ee` / `engineering-exit`，默认在 gates 通过后按全局 Git 规则和 `gitlab.flow` 对当前 scope 完成本地 commit；push 和创建/更新 MR/PR 需要用户对本次交付的明确授权。`prepare-only`、`no commit` 等措辞收窄本地提交权限，`local-only` 表示仅本地收尾。不因收尾扩入 `separate-ready` concern：仅对用户已授权、可归因且独立验证的 concern 单独提交并点名；来源不明或无关修改保留。收尾不授权破坏性清理、issue/label/release 状态变更或 force push。gate 失败不得执行受影响的 Git 写入。

在上述授权范围内，按项目 `index.md` 的 `gitlab.flow` 执行：

- `l1`：仅在非 default topic branch commit/push/open MR；release-impact unknown 阻止远端写入，纯 post-merge unknown 留 exact action。
- `l2`：同样使用非 default topic branch；非关键 release unknown 需用户接受风险。
- `l3`：gates 通过后可 commit 当前分支；获远端授权后可 push，非 default branch 按授权开 MR，default branch 不适用 MR。默认免 review-router/GitLab settings lint；用户或项目指定评审仍执行，其他工程 gates 不减。
- missing/unknown：本地 commit 遵循全局分支限制；远端 package 只准备，待 flow 明确后执行远端动作。

## Conditional References

只加载命中 gate 的直接 reference；specialist 也由本入口路由，不继续向下串联：

- plan、durable docs、ADR 或 source comment 生命周期：`references/doc-lifecycle.md`。
- agent docs、architecture/source-map 或 release preflight：`references/review-gates.md`，并按域运行 `../agent-doc-hygiene/SKILL.md` 或 `../doc-arch-review/SKILL.md`。
- 风险、release、review 或外部事实混合证据等级：`references/evidence-classification.md`。
- 准备或更新 MR/PR package：`references/mr-template.md`。
- 存在 exact loop-ledger 或当前 route 的 context-backed final-form：`references/state-closeout.md`。

## Hard Gates

- 删除须先列 exact paths 并确认；已证明完成的 exact final-form recovery route 是唯一窄例外。
- 解释整个 dirty worktree。未知、WIP、blocked 和 failed-check 修改不得 revert、隐藏或混入提交。
- 探索中的架构、命名、source of truth 或 skill 行为不因 exit 获得写入授权。
- 移出 scope 的内容不留解释其缺席的残留；仅保留有当前证据的安全、兼容或外部契约边界。
- branch/default/`gitlab.flow` 未检查前不 commit/push；flow missing/unknown 按上文处理，force push 永远需单独授权。

## Workflow

1. **Resolve scope**：识别 roots、当前/default/target branch、平台、flow 和 plan；检查 status/diff。把 dirty paths 分为 `current-scope`、`separate-ready`、`preserve`、`unknown`，记录 reason/next action。未确认删除停在该删除动作，继续其余已授权准备。首次 push 或已有 MR 时 fetch target 并检查分叉；rebase 前保护 preserve/unknown dirty。
2. **Verify implementation**：复用当前 revision 的有效验证，补齐项目必需 checks 与最窄 smoke/acceptance；仅因新改动、失败或未解决风险扩大或重跑。无法验证时说明缺失依赖与替代证据。
3. **Run review**：`l1/l2/unknown` 直接读取 `../review-router/SKILL.md`，以 `caller=engineering-exit` 从 simple 开始且最多升级一次；`l3` 仅在用户或项目要求时运行指定评审。修复 blocking findings 后重跑相关检查；非阻塞扩展记录为普通 follow-up，用户或现有 contract 要求 work order 时才形成 final-form。
4. **Synchronize docs**：行为、接口、配置、runtime、example、workflow 或 agent entrypoint 变化时同步 owner；重大结构变化检查 source map、architecture index 和 AGENTS pointer。
5. **Run doc gates**：按 Conditional References 直接加载生命周期、agent-doc 或 architecture gate。普通 source-to-doc sync 不升级为 broad specialist audit。
6. **Prepare release/MR**：`l1/l2` 或 release-ready 请求执行 preflight；`l3` 默认跳过。按 `mr-template.md` 准备并校验 headings。
7. **Close matched state**：仅对当前项目的 exact loop-ledger 或 context-backed final-form 按 `state-closeout.md` 处理。报告 exact ledger path 供显式 audit follow-up 使用；不 dispatch/wait audit，也不归档 ledger。
8. **Execute git exit**：复核 staged scope、branch、flow 和 checks；按 Git Exit Authority 完成本地提交及已授权远端动作，保留 preserve/unknown。MR/PR 写后按 `mr-template.md` 回读 identity、保护段和 CI attachment，并遵循其中的等待边界。

## Exit Criteria

- dirty paths 全部分类；保留/未知项有 reason/next action；实现、验收和必要 smoke 已通过，或 skipped 项有原因与替代证据。
- applicable review/docs/release/MR gates 均为 passed、not applicable、blocking 或明确 follow-up。
- durable docs 描述 target state；ADR 只记录长期跨边界决策；MR package/readback 与 diff、`mr-template.md` 一致；state closeout 只处理 exact match。
- 远端交付前已证明 HEAD 相对当前 target branch 的 freshness；需要 rebase/merge 时已完成或停在授权 gate。
- git 写入仅含已验证 scope，远端动作均在当前授权内。

## Output

中文先给终态，再报告 scope、checks、dirty、gates、MR、风险和动作；仅按需展开模板。
