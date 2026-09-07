# Project Initialization

用于 `/cc init`、初始化 `coding-conventions`、向项目 `AGENTS.md` 注入模板、配置模板附属 hook、接入 Node test kit，或更新普通模板规则。先扫描目标与现有配置；用户已明确目标模板和改动范围时直接完成，否则展示具体候选供确认。

## Scan And Selection

1. 读取目标 repo 最近的 `AGENTS.md` / `CLAUDE.md`、README / CONTRIBUTING、构建与测试配置，以及既有 `coding-conventions:begin/end` 受控块。
2. 从 package、Gradle、Python、CLI、前端和测试信号选择模板。`general` 是所有项目基线；父级已有 `general` 时子项目不重复。
3. Repo 已有团队维护的 AGENTS / CLAUDE / README / CONTRIBUTING 或 CI 约定时，默认按团队 / 外部项目处理，并排除 `../preferences/*`、个人本机路径、私有 helper 和个人 workflow。
4. 展示：已接入、推荐接入、可选接入、已验证的附属资源；Node 项目还要说明推荐 `node-js` 或 `node-ts-build`、将新增的配置与 npm scripts。
5. 复用用户已选定的组合与范围；仅在模板组合、hook 或构建接入仍未确定时，给出具体候选并询问一次。

## Managed Blocks

- 把确认的模板写入 `AGENTS.md` 的 `coding-conventions:begin <template-id>` / `coding-conventions:end <template-id>` 受控块，默认置于项目自身规则之后的 `## 编码规范` 或等价小节。
- 新项目先写 `general`，再写测试、语言或工具模板。个人 / 自管项目已有其他 block 但缺 `general` 时，先检查父级；父级没有才补。
- 模板标题整体降级，避免与项目文档主标题竞争；更新既有同名 block，不制造重复块，不修改 marker 外内容。
- 团队项目中既存的个人偏好或个人路径应移出项目入口；不要把 `preferences/*` 展开到具体项目。
- `../preferences/*` 不是独立模板；`sync-conventions.sh` 只把 `general.md`、`java.md`、`review.md` 写入个人父级 `~/Documents/projects/AGENTS.md` 的 `general` 受控块，其余偏好按主 skill 的信号条件读取。

## Node Test Kit

`../node-test-kit/` 只维护 runner orchestration、fresh-build preset、共享 fixture、V8 coverage 和 entrypoint 诊断；项目继续直接使用 `node:test` / `node:assert`，只保存 `node-test.config.mjs`、标准 npm scripts、业务 fixture、断言与项目预算。

- Node-only CLI / server 选 `node-js`；需要测试编译产物的 TypeScript 项目选 `node-ts-build`，标准 test 必须先 build，不能读取旧 `dist`。
- V8 是 coverage / profiler 数据源，不是 runner。只有真实消费者存在时才讨论 Vitest adapter，不为统一迁移现有项目或预建无消费者 preset。
- 用 `node-test-kit init --preset <node-js|node-ts-build>` 创建薄配置；仍受上述扫描、披露和确认 gate 约束。

## Hook Partials

- 模板目录可提供 `pre-commit-hook.partial` 或 `pre-push-hook.partial`；实现只维护在 partial，不复制进模板正文。
- 注入前必须在目标 repo 实际运行并证明 partial 调用的命令、Gradle task 或脚本存在且通过。formatter hook 的 probe 至少覆盖 staged 修改、staged 删除，以及同一文件同时存在 staged / unstaged hunks：删除路径不得传给 formatter，原有删除仍保持 staged；hook 必须拒绝或保留未暂存 hunks，不能把它们带入 index。失败时报告，由用户决定调整或放弃。
- 候选清单必须提前披露 partial、目标 hook、行为和验证结果；确认推荐组合即确认已列出的 partial，未列出的不得写入。
- 只注入模板提供的 partial，不临场编写。用 `git rev-parse --git-path hooks/<hook-name>` 定位当前 clone / worktree 的统一 hook。
- Partial 使用受控 block；有同名 block 时与当前 partial 比较并原位更新，没有时追加，保留 marker 外内容。无 marker 的 hook 若能与已知旧版 partial signature 精确对应，先披露迁移 diff 并在获得确认后替换该旧 block，不要与当前 partial 叠加执行；无法可靠归属的 markerless 内容保持不动并报告。目标 hook 不存在时才创建最小 `#!/bin/sh`、`set -e` 入口，并确保可执行。
- 同一 hook 中多个 block 串行执行；partial 不得用顶层 `exit 0` 跳过后续 block，无相关变更时用条件块跳过自身逻辑。
- Hook 是本地配置，不把生成文件、个人 hook 路径或安装状态写进项目源码或提交记录。

## Template Updates

更新普通模板时，先确定目标模板；若内容是 pitfall，转到 `pitfall-maintenance.md`。按用户已明确的规则只改对应模板；规则或范围未定时展示现状与拟写内容并确认。运行该模板或同步器已有的最窄验证。

完成注入后，报告未被模板 partial 覆盖的 CI、Git hook 或 verify 缺口；不要临场补写新的 hook。
