---
name: agent-assignment
disable-model-invocation: true
description: 在非简单实现、调试、验证、评审、研究或多步任务中，按职责、独立产物与可观察净收益选择 direct、RS 或 internal；短问答、单次确定性命令和可直接闭环的单点小改不使用。
---

# agent-assignment

GPT-6 Sol medium 持有需求、关键判断与验收。本 skill 只决定执行分流：优先使用健康的 RS 交接完整职责；internal 需要可观察的净收益。委派率不是验收指标。

## 委派准入

- 在非简单任务首次广泛扫描、修改或其他实质工具调用前，用一句过程更新明确选择 `direct`、`RS` 或 `internal`，并据此执行。
- 每个非确定性的完整职责，先检查 RS 能否凭精确来源和有限 brief 交付可抽样验收的产物。健康且可用时优先派 RS；无并行工作也可成立，但不拆微任务凑派单。一个职责至多一个 worker。
- RS worker 不继承主线已加载的个人规则。只读 brief 须绑定适用规则来源和验收；写入、Git、删除或外部动作前须证明 worker 已加载规则且 Host 覆盖副作用，否则保持 RS 只读。
- 职责边界明确、产物可独立验收只是必要条件，不单独证明 internal 有收益；internal 另按下述净收益门槛判断。
- 能靠必要事实与精确来源独立完成时，只交接目标、权限、产物和验收；确需完整主线上下文则 direct，并说明依赖。
- internal 还须有明显并行收益，或替代一段实质工作且主线只需抽样；若派发后只能等待，或主线仍须重做大部分证据，选择 RS 或 direct。
- 短问答、确定性命令、单点小改和无法交接的职责用 direct；确定性工作优先脚本或 CLI。对原本适合 RS 的职责选择 direct 时，说明来源、验收、运行态、写入冲突或健康等具体障碍。
- 若平台 gate 是“除非用户或适用的 AGENTS / skill 明确要求，否则不得主动委派”，本 skill 只对满足上述准入的非简单职责提供委派授权；仍遵守平台的并行与工具可用性边界。
- 出现新的独立职责，或主线准备开始下一段实质取证、审查、实现或验证时，重新应用同一准入；不得把初始 `direct` 判断沿用到新出现的可交接职责。结果仍为 `direct` 时继续主线。
- 使用能覆盖职责的最少执行者。多个独立产物且无写入冲突时才并行；同一职责默认一个 worker，主线保留整体验收。
- CI 等确定性等待不参与自由分流。用户目标要求关注 `pending/running` 的 pipeline/job 时，先绑定 exact source/revision、验收终态、等待预算和回传任务，按 `references/dispatch-execution.md` 派 RS；取得匹配的接受回执才算交接。主线不得自行轮询或等待；接入失败只对原来源做一次有界核验，保留未完成 oracle。用户明确不等待时遵从。

## 路由档位

确定性字段提取、格式转换、批量校验或规则明确的变换优先使用已有脚本、CLI 或短命令，不为分层而启动 agent。

对候选和判定标准明确的语义分类、选择、排序或适用性检查，优先按 `jev-evaluation` 使用 Jev，避免仅为这类判断启动 worker。Jev 是 direct、RS 和 internal 都可调用的工具，不是第四类 agent；取证、实现、多步推理与验收仍按本 skill 分流。Jev 返回的路由建议须经过现有准入和权限核验。

| 档位 | 适用范围 | 外部候选 | 内部委派 / 接续 |
| --- | --- | --- | --- |
| 轻量执行 | 定向取证、材料整理、小范围修复，验收容易独立核验 | DS fast | `gpt-6-luna` medium；极短、低歧义且脚本不适合时用 low；确有推理深度缺口时用 high |
| 标准工程与分析 | 范围已确定的多文件实现、技术验证、较长追踪、材料综合与审查 | 技术执行用 DS pro；广泛阅读和文字综合用 Kimi | 边界清楚且容易抽样验收用 `gpt-6-luna` medium，确有推理深度缺口时用 high；多步工具操作、权限或运行态判断、返工代价高时用 `gpt-6-sol` medium；`gpt-5.6-terra` medium 保留为同类任务的对照候选 |
| 疑难判断 | 未收敛的复杂根因、架构约束冲突、关键设计评审 | 不强行寻找外部等价档 | `gpt-6-astra` medium，只有用户明确决定才引入 |

- 仅为推理或检查深度不足提高 effort；多步状态、权限或工具可靠性优先影响模型选择。任务变长、测试失败或额度用满不自动触发升级。
- 对照期间按 exact Agent/model/effort 与任务类型读取真实产物、验收、返工和用量；样本不足时只作个案观察，不凭原始成功率或少量样本移除 Terra。
- GPT-6 Sol medium 是主线默认档位。Sol 子 agent 只有在独立产物能带来明显的并行时延或独立验收收益时才成立；同模型委派不视为节省 Codex 用量。主 agent 先把复杂问题收束成有界任务，不能仅因改动多或测试失败升级 Astra。
- `internal` 显式传入目标 `model`、`reasoning_effort` 和 `fork_turns: "none"` 或正数轮次，不继承主线模型。
- 档位不可确认或不可用时重新比较 direct 与可用路线，不临时修改注册配置。

## Conditional References

- 已选择 RS 或 internal，准备派发、接续或处理失败时，读取 `references/dispatch-execution.md`；它拥有 exact route identity、preflight、handoff、writer 切换、失败接续和执行后的成本评估。
- 大范围源码证据索引、显式 Codex/RS 独立对照或用户要求 Council / deliberation 时，读取 `references/evidence-comparison.md`。

只加载命中的一层 reference。用户要求单开任务时使用任务创建入口；要求原生 subagent 时使用内部委派入口，不把两种授权互相替代。主 agent 始终负责验收关键证据、整合和最终判断。
