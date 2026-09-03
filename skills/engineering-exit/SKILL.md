---
name: engineering-exit
description: "engineering-exit / ee: 收束实现后的源码、文档、验证证据和 MR 准备。适用于用户说 ee、engineering exit、工程收尾、准备提审、开 MR 前收束、ship this change，或要求把 plan 转为终态 docs/ADR 后开 MR。"
disable-model-invocation: true
---

# engineering-exit

收束实现后的源码、文档、验证和 MR package；不用于设计、context 保存或简单修复。

## Privileged Git Exit

用户选择 `ee` / `engineering-exit`，即授权 gates 通过后按 `gitlab.flow` 对当前 scope commit、push 和创建/更新 MR/PR；`prepare-only`、`local-only`、`no commit/push/MR` 等措辞收窄授权。授权还可覆盖可归因、独立验证、单独提交并点名的 `separate-ready` concern，不覆盖来源不明修改、破坏性清理、issue/label/release 状态、force push 或无关工作。控制边界不明时只问一个问题；gate 失败不得 git 写入。

按项目 `index.md` 的 `gitlab.flow` 执行：

- `l1`：仅在非 default topic branch commit/push/open MR；release-impact unknown 阻止远端写入，纯 post-merge unknown 留 exact action。
- `l2`：同样使用非 default topic branch；非关键 release unknown 需用户接受风险。
- `l3`：gates 通过后可 commit/push 当前分支；非 default branch 默认开 MR，default branch 不适用 MR。跳过 review-router 和 GitLab settings lint，不跳过实现、文档、loop-ledger、context 和 git hygiene。
- missing/unknown：只准备 package，不使用 push/MR 特权。

## Conditional References

只加载命中 gate 的直接 reference；specialist 也由本入口路由，不继续向下串联：

- plan、durable docs、ADR 或 source comment 生命周期：`references/doc-lifecycle.md`。
- agent docs、architecture/source-map 或 release preflight：`references/review-gates.md`，并按域运行 `../agent-doc-hygiene/SKILL.md` 或 `../doc-arch-review/SKILL.md`。
- 风险、release、review 或外部事实混合证据等级：`references/evidence-classification.md`。
- 准备或更新 MR/PR package：`references/mr-template.md`。
- 存在 exact loop-ledger artifact：`references/state-closeout.md`；只形成 audit handoff，不投递 audit。
- 当前 route 仅存在 exact context-backed final-form：只读取 `references/state-closeout.md`。

## Hard Gates

- 非 `ee` 请求的 commit/push/MR/远端描述更新仍需明确确认。
- 删除须先列 exact paths 并确认；已证明完成的 exact final-form recovery route 是唯一窄例外。
- 解释整个 dirty worktree。未知、WIP、blocked 和 failed-check 修改不得 revert、隐藏或混入提交。
- 探索中的架构、命名、source of truth 或 skill 行为不因 exit 获得写入授权。
- 用户已否定或移出 scope 的内容不得留下只为解释其缺席的注释、文档、测试、配置、changelog 或 MR 文案。仅保留有独立当前证据的安全、兼容或外部契约边界。
- branch/default/`gitlab.flow` 未解析前不 commit/push；force push 永远需单独授权。

## Workflow

1. **Resolve scope**：识别 roots、当前/default/target branch、平台、flow 和 plan；检查 status/diff。把 dirty paths 分为 `current-scope`、`separate-ready`、`preserve`、`unknown`，记录 reason/next action。未确认删除只继续只读 gates。首次 push 或已有 MR 时 fetch target 并检查 merge-base/behind/divergence；rebase 前保护 preserve/unknown dirty。
2. **Verify implementation**：运行项目原生 checks 和最窄有意义的 smoke/acceptance；无法验证时点名缺失依赖与替代证据。
3. **Run review**：`l1/l2/unknown` 直接读取 `../review-router/SKILL.md`，以 `caller=engineering-exit` 从 simple 开始且最多升级一次；`l3` 跳过。修复 blocking findings 后重跑相关检查；非阻塞扩展写成 final-form。
4. **Synchronize docs**：行为、接口、配置、runtime、example、workflow 或 agent entrypoint 变化时同步 owner；重大结构变化检查 source map、architecture index 和 AGENTS pointer。
5. **Run doc gates**：按 Conditional References 直接加载生命周期、agent-doc 或 architecture gate。普通 source-to-doc sync 不升级为 broad specialist audit。
6. **Prepare release/MR**：`l1/l2` 或 release-ready 请求执行 preflight；`l3` 默认跳过。按 `mr-template.md` 准备并校验 headings。
7. **Close matched state**：仅对当前项目的 exact loop-ledger 或 context-backed final-form 按 `state-closeout.md` 处理。报告 exact ledger path 供后续 `save-context` 或显式 audit follow-up 使用；不 dispatch/wait audit，也不归档 ledger。
8. **Execute git exit**：复核 staged scope、branch、flow 和 checks；按 concern commit，再 push/open/update MR。不得夹带 preserve/unknown 或 force push。MR/PR 写后按 `mr-template.md` 回读 identity、保护段和适用 CI attachment；默认不等待 CI/mergeable，除非用户要求 merge-ready，或项目 source of truth 把 CI success 定义为 exit oracle。

## Exit Criteria

- dirty paths 全部分类；保留/未知项有 reason/next action；实现、验收和必要 smoke 已通过，或 skipped 项有原因与替代证据。
- applicable review/docs/release/MR gates 均为 passed、not applicable、blocking 或明确 follow-up。
- durable docs 描述 target state；ADR 只记录长期跨边界决策；MR package/readback 与 diff、`mr-template.md` 一致；state closeout 只处理 exact match。
- 已证明 HEAD 相对当前 target branch 的 freshness；需要 rebase/merge 时已完成或停在授权 gate。
- git 写入仅含已验证 scope，远端动作均在当前授权内。

## Output

中文先给终态，再报告 scope、checks、dirty、gates、MR、风险和动作；仅按需展开模板。
