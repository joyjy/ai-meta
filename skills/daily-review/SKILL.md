---
name: daily-review
description: "回顾前一日工作，修复已登记摩擦，完成审计结算与验证状态汇报。"
disable-model-invocation: true
---

# daily-review

执行“前一日工作回顾与机制改进收口”。时区固定 Asia/Shanghai，回顾前一自然日 00:00–24:00。先读取本 automation memory，避免重复上一轮已结论化的问题。

取材前先运行一次 `~/.ai/scripts/daily-review-collect collect --date <被回顾日期>`，得到 `daily-review.collect.v1` 事实包。事实包只提供确定性事实，不含裁决；其中 `gaps` 与 `limitations` 按“关键来源缺口”处理。CLI 失败时报告 exact 错误，再按下文取材边界人工补齐，不得据此推导无人工作。

## 核心目标

主任务不是复述 Audit，也不是按工具失败列问题，而是从真实工作中改善 agent 的默认决策函数：

> 在不越权、不跑偏的硬约束下，持续推进用户真实目标，直到获得可验证结果。

每日保留三个独立分析维度，但不要求每天都有新结论或分别输出栏目：

- 行为机制改进：识别真实工作中的 overreach、drift、stall，按证据决定是否纠偏。
- 自动化与自主交付分析：从成功事项、重复工作和未完成交付中识别能取消的具体人工操作或接力，说明最小改动与可验证结果。已有自动化正常运行只作为能力证据，不算新机会；仅当出现新的可复用场景或可消除的人工作业时才提出建议。

- 观点发现：从具体工作中发现值得学习、争论或试验的观点，说明真实案例怎样挑战已有理解、形成什么判断、会改变什么决定；不要求立即减少人工操作或落成规则。

三个维度独立裁决。“无新的纠偏建议”不等于“没有自动化机会”；某个执行平台或准入文件不可用，只限制该平台的适配结论，不能取消工作层面的自动化分析。

三个行为评价轴：

1. overreach：是否执行未授权副作用、扩大 authority 或越过 human checkpoint。
2. drift：是否偏离用户目标、scope、约束或 acceptance，把内部概念、最近 context 或实现便利当成目标。
3. stall：目标与 authority 已明确时，是否停在分析、计划、artifact 或重复确认，迫使用户催促或手工接力。

authority 与 intent fidelity 是硬约束；满足后优先减少用户纠正、催促和接力，并最大化 verified outcome progress。

## 增量价值门禁

先与 memory 和已有 durable owner 比较，再决定是否展开。以下才是值得报告的增量：
- 新证据改变了既有结论、风险判断、处置或实验设计；已知问题只报告这个变化，不重讲原则。
- 新发现满足下述分层处置条件，且会改变实际选择：单例可支持原 owner 的局部修复或对照试验；跨项目默认规则修订仍须通过行为机制建议准入。局部工具摩擦按原 owner 结算，不扩写成整篇机制主题。
- 新机会能具体说明“哪一个人工动作可以取消、补什么就能做、为什么现在值得做、如何确认完成”，并有昨日实际工作证据。
- 新观点由具体案例支撑，揭示了此前忽略的区别、取舍或适用边界，能改变理解或实际决定；不以出错、高影响、跨案例复发或立即可自动化为前提。

同一 signature、同一建议换场景重述、仅增加 recurrence、已有自动化正常运行、规则已修改但无新行为样本、仍缺同一个文件或仍 pending，都不算实质新增。已实施的建议只验证效果，不再次建议实施；“已经修改”仅关闭实施项，不能自动关闭效果判断，须核对修改是否作用于原失败点。去重按下一步是否变化，不按问题是否见过；同一问题出现有直接证据的新失败原因、修复位置或可区分的验证办法，才重新展开，不能仅因增加一次 occurrence 重报。尚未执行且条件未变的实验不每天重提。

试验、观察和已实施待验证项在 memory 记录登记日期。能冻结成场景的项按「改动项的验证与落地」处理。无法冻结的项登记后 14 天内没有匹配样本时，判为 `expired`，即未出现、停止追踪。expired 项在当轮日志写一行，然后从 memory 删除。

取证和内部判断仍须完成；输出长度取决于值得处理的信息，不为填栏目、满足数量或篇幅配额扩写。三个分析维度分别裁决，允许全部无新增；没有纠偏或自动化机会时，仍可有值得报告的新观点。不得为追求新颖而扩大扫描范围、降低证据门槛或虚构用户成本。

## 前置硬门禁

1. 先做最小取材，判断前一日是否至少有一项“人主动发起且发生实际推进、交付或决策”的工作。automation、自主后台维护、审批/权限子任务、context 加载/恢复、无副作用定时跳过不算人工工作。
2. 无论是否有人工作，每次运行都完成独立 Audit / LL review 结算和「Open 摩擦修复」。
3. 若足以确认无人工作：跳过行为机制分析与其他 automation 的 memory hygiene。Audit/LL、Open 摩擦修复、已提交盲测的收取与落地、本 automation 的 memory 整理照常执行。无修复结果和决策项时不建日报，返回 `NO_FINDINGS`；有修复或决策项时按正常输出记录。
4. 关键来源失败或扫描不完整时不得推导无人工作，报告 exact 缺口。
5. wall-clock 跨日、未开机或没有 automation run 不构成 recurrence、噪音或 aging；只按实际 receipt、独立 occurrence 和 status transition 判断。

## 前一日取材边界

1. 先读前一日 Daily Note、相关 project context、automation memory / run receipt。
2. 会话历史只走本地只读 date-bound manifest，不调用线程列表工具。事实包 `threads` 是召回清单，`client` 字段标明客户端：
   - 召回规则是 `created_at_ms < end_ms AND updated_at_ms >= start_ms`，updated 只用于召回。Codex 条目查询 `/Users/example/.codex/state_5.sqlite`，`rollout_found=false` 的条目已记入 `gaps`。Claude Code 条目来自 `~/.claude/projects/<project>/<session>.jsonl` 主会话，不含 subagent 记录；
   - Codex：读取 `/Users/example/.codex/sqlite/codex-thread-summaries-dev.db` 对应 summary（存在时），从 exact rollout_path 仅提取窗口内 user/assistant turns、terminal event 与末尾必要上下文；长任务不从头读；
   - Claude Code：没有 summary DB，从 exact rollout_path 仅提取窗口内 user/assistant 记录与末尾必要上下文；长会话不从头读。`entrypoints` 含 `sdk-cli` 表示会话由程序启动，例如 RS 派发的节点。`human_turns` 是窗口内人发起的轮次数。这两个字段只是判断「人主动发起」的事实；
   - 只有 rollout 内有窗口期实际推进/交付证据才纳入；纯 load-context、状态刷新、mtime 或 updated time 不算工作；archived task 同样使用 exact rollout_path。
3. 主分析只读取 turns 自然出现的本地文件、MR/Issue/文档链接作为 anchors。Open 摩擦修复另可沿选中条目的 exact owner 和证据定位源码。不横扫 repo、GitLab 或原始聊天历史。
4. 只有 direct error、terminal timeout 或可复现 probe 才判工具故障；外层等待只写“未取得结果”。
5. state DB、summary DB、rollout 或关键来源缺失、锁定、失败、截断时记录 exact 缺口。

## 主分析顺序

在读取本轮新的 `agent-audit.yaml` findings 前，先在工作记忆中冻结步骤 0–6 的行为候选结论、自动化与自主交付分析及观点候选；之后 Audit 只能反证、降级或补充，不能接管议题。

0. **现有机制 inventory**：用户反馈行为不符合预期时，优先还原当时实际加载的规则和连续对话。检查规则暗示、条款冲突、适用范围过宽和执行偏差，再判断原因。规则存在不等于当时已加载，当前版本也不能替代历史版本。优先修正原有条款，避免直接归因于模型或叠加新规则。对每个可能的行为问题，先定向查当前已有的 prompt、gate、skill、tool-route、context/readback、FF/LL contract、previous experiment 或 durable owner。记录它试图改变的默认行为、加载/触发条件、当日是否实际触发及当前状态；不做无边界全局扫描。先判断“机制不存在”还是“已有机制未生效”，再分析失效。对影响该判断且现有授权内可查的缺口，按已召回的 exact rollout 与 owner 定向核验当时实际注入/读取的内容、关键选择点和用户确认；相关早期规则只取必要片段，不重读长任务全文。进入 watch / inconclusive 前先完成这些可得历史的核验；来源不可用或核验仍不足时写明已查范围与 exact 缺口，不无限扩搜，也不等用户催促才查。
1. **真实目标与结果**：内部逐项核验“真实对象 + 用户要改变什么 + 实际动作/决策 + 结果/当前状态 + terminal oracle”；同时标出哪些步骤已由 agent 独立完成、哪些步骤仍由人重复操作或接力，以及这些人工步骤是必要决策/权限边界还是可消除的执行负担。成功事项与纠错事项同等取材。
2. **关键选择点**：识别 agent 何时选择继续、停下、追问、猜测、扩 scope 或收口。
3. **代理目标**：在规则与上下文核验后，推断该选择实际优化了什么，例如降低自身不确定性、尽快产出 artifact、复用最近 context、减少责任或默认 helpful continuation。
4. **用户成本**：检查是否造成再次催促、方向纠正、内部 ID/术语补充、手工接力、越权后果、等待或结果遗忘。先区分用户新增要求与原目标下的执行缺口；按用户仍承担的关键判断、纠偏和交付接力负担排序，不因某个小改动易实现或易验收而优先报告。
5. **反事实默认**：在相同信息、scope 与 authority 下，更好的 agent 应如何选择；普通内容字段可据证推断，`owner / source_identity / authority / terminal_oracle` 缺证据时保持 `unknown`。
6. **跨 case signature**：多个事项共享同一决策逻辑，或单一 case 造成高影响，才准入跨项目默认规则修订。未达到该门槛不否定具体问题，也不阻止原 owner 的局部修复或对照试验建议。先定位行为策略，再定位 prompt、gate、tool-route、skill、context、artifact/readback、owner/authority、acceptance 或 settlement owner。
规则冲突的持续收口：遇到本窗口实际影响选择的冲突时，按 `agent-doc-hygiene` 的冲突检查定向核对当时实际加载的条款、用户纠正和原 owner，不横扫所有规则。分别判断业务事实是否已知、当前有效政策是什么、还缺哪项决定；不得把政策未对齐当成事实未知而让用户重复确认。按全局 instructions 的冲突裁决规则核验当时可继续的授权路径和原验收，既不默认越过停止条件，也不以“按规则停下”结算整个目标。具体修复优先替换旧条款或收窄适用条件，不叠加平行规则；记入 memory 只作桥接。当前业务终态、原 owner 修复/消费者读回、目标版本后的真实行为效果分别结算。具体改动按「改动项的验证与落地」验证和落地。下一轮只因修复状态、盲测结果或匹配行为证据变化重新展开，条件未变不每日重提。

7. **Audit 反证**：最后用 Audit 检查遗漏、反例和合同偏差；不得因 candidate 数量、promoted 或 severity 自动改变主题。
8. **上一轮验证**：对 memory 中实验判定 validated / inconclusive / falsified / superseded / expired。已提交的盲测按「改动项的验证与落地」收取结果。无法冻结的项没有新的真实行为证据时保持 inconclusive，登记满 14 天转为 expired。

## 观点发现


观点的长期来源是 `/Users/example/Documents/me/Resources/工作观点.md`。开始观点分析前读取该笔记，按其中维护约定与已有判断、边界及来源查重。用户已授权本自动化维护这份笔记：仅在本轮真实证据带来实质增量时，更新对应稳定编号条目的证据、判断、适用边界、价值与成熟度或下次观察点；确属不同判断时才新增条目。被推翻或合并的条目保留编号、简短理由及后继指针，不删除。无变化不改日期、不追加每日记录。每日报告只呈现本轮变化并链接该条，automation memory 只留笔记指针和必要待决信息，不复制观点正文。来源缺失时记录限制，不用报告自述提升成熟度；文件读取失败时不得另建平行观点库。本节只授权维护这份观点笔记。实验和规则改动只按「改动项的验证与落地」执行。

从同一批真实工作证据中独立寻找观点，不只从错误和用户纠正取材；成功做法、反例、取舍及意外结果同样可用。用自己的判断说明为什么值得注意，不能把所有发现都改写成“补证据、加门禁、更谨慎”，也不为制造新颖而追求反直觉。

每个入选观点用自然语言串起：原来怎么理解（没有证据时只称待检验假设，不虚构大家的共识）→ 哪个真实案例挑战或细化了它 → 新的判断及适用边界 → 以后会因此作出什么不同决定。保留具体业务关系和关键反例，避免抽象成脱离案例的常识口号。

价值与成熟度分开：价值看能改变什么重要判断及潜在适用面；成熟度据证区分单例观察、待验证假设、已在真实场景验证或已有独立复用，不用“有潜力”冒充可靠。一个有证据的单例可以提出有价值的假设，不必先满足行为纠偏的跨case门槛；若进一步建议修改默认规则或自动化执行，仍须分别通过原有准入与权限边界。

只输出0–2个有实质增量的观点；不凑数、不恢复每日论坛/议会/自评流程，不强迫每个观点生成checklist、skill或任务。值得验证时给出最小区分性问题或实验：什么结果会支持、推翻或收窄它；没有必要实验时明确保留为观察即可。已知观点仅在新证据改变判断或适用边界时重提，单纯换案例不算新增。观点与纠偏/自动化机会指向同一发现时合并叙述，不重复计数。

## 行为问题分层处置与机制建议准入门禁

分别裁决问题成立、局部处置和跨项目推广，不用同一个门槛替代三者：

- **具体问题**：一次直接证据即可成立，但须证明它是原目标与授权下的执行缺口，而非后续新增要求。问题重要性不由是否新颖或是否足够推广决定。
- **模型与推理强度**：每个行为问题标注关键选择点当时的客户端、模型与推理强度，来源是事实包 `threads[].client` 与 `threads[].models`。自动化运行同时附 `threads[].automation.configured`。去重 signature 包含 owner、客户端、模型与推理强度。同一问题在同一模型与推理强度下第 2 次出现时，首个改动项是可回退的配置改动。配置改动指换模型或推理强度。该改动项用盲测比较原配置和新配置。prompt 或规则改动排在配置改动之后。只有一种配置的样本，不能单独归因于模型。
- **局部修复 / 对照试验**：有证据的单例即可提出；须明确当时的关键选择点、已有尝试、原 owner、最小改动、权限边界和可证伪验收。允许验证假设，不将单例包装成通用机制。历史回放须隔离后续纠正信息，保留适用边界或反例；只能作为筛选方案的证据，不能冒充真实运行有效。
- **跨项目默认规则修订**：须同时满足下面的完整准入条件。已有规则不生效时先定位失效环节，不默认继续加规则；加载、工具或运行链路缺口应落到各自原 owner。临时限制可控制风险，但不能作为原目标已完成的证据。

跨项目默认规则修订必须同时满足：

- 先写清已有尝试及 durable owner；若声称失效，必须证明失效形态属于未加载、触发过晚、仅 advisory、owner 错位、不可执行、缺 terminal oracle、只修实例未改默认，或其他有直接证据的机制缺口。
- 改变 agent 在关键选择点的默认行为，而非只修 CLI 参数、路径、格式、测试或单个 artifact。
- 能减少至少一种真实用户成本：再次催促、纠正方向、补内部信息、手工接力或处理越权后果。
- 同时控制 overreach、drift 和 stall；不用“更谨慎”制造停滞，也不用“更主动”扩大 scope。
- 有跨 case 证据，或单一高影响证据。
- 有可证伪的下一次行为实验。

不满足跨项目准入者先按上述局部处置条件裁决；只有也不足以支持具体修复或区分性试验时，才进入 audit settlement、tool friction、watch 或 not_mechanism，并明确缺什么。规则存在只证明有机制；没有当日失效证据可判 keep，但不能据此判 validated。只有满足版本/加载边界与声明验收的真实正向样本才能判行为有效；无匹配样本保持 inconclusive。已证明失效时优先补强原 owner，不新增平行规则。既有 signature 仅增加 recurrence、但 disposition、默认策略和实验均未变化时，只更新 evidence，不得再次进入建议。允许输出“本轮无新的行为机制建议”。

局部处置按本节条件紧凑说明，不机械套跨项目建议模板。每个准入的跨项目建议写：旧默认、代理目标、用户成本、新默认、适用条件、fail-closed 边界、跨事项 anchors、owner、最小实验、acceptance、human checkpoint、下次回看条件。报告必须回答为什么旧默认自然发生、何时合理、何时越权/跑偏/停滞，以及如何证明新默认更好。

## Steelman 与处置

- 区分已验证 pattern、一次观察、已有机制补强、纯 context、业务问题和工具摩擦。
- 批评或降级前构造当时约束下最强合理解释；Steelman 后仍明确 keep / change / experiment / watch / not_mechanism。GUESS 不升级为事实。
- 检查前一日 automation 是否有用或产生人工补救；本回顾自身后续收到的纠正与催促，由下一轮按窗口内真实人工跟进纳入同等分析，核对是否在已有目标、授权和可查证据下过早收口，不将用户“继续/试试”视为原本就必须取得的新授权。「改动项的验证与落地」允许的盲测 Run 和落地改动之外，不修改其他 automation、项目源码、skill、tool-route、active FF/LL，不创建任务或 Run。

## 自动化与自主交付分析

本节是独立主分析，不是行为纠偏的附录，不受“跨 case 失效或单一高影响错误”准入门槛约束。一次真实成功闭环也可支持复用机会，但不能据此宣称稳定或跨场景可靠。

1. 从昨日代表事项逐项扫描三类机会：已成功自动完成、人工反复做或接力、已授权但尚缺最后交付步骤。优先找“少量完善即可自主完成”的具体工作；不把泛化的更主动、加规则或继续修 bug 当作自动化分析。
2. 对每项先给工作层面的判断，再选择实现载体：无需新增机制、固定脚本/批处理、当前任务自主接续、Codex 定时自动化、事件驱动 RS、其他或 unknown。模型与平台是后续适配项，不预设 Kimi/DS，不因某个平台不可用否定整个机会。只有需要比较 Kimi/DS 时才依据当日可验证能力选择 Kimi / DS / either / unknown。
3. 已有自动化先查其 owner、触发、产出和真实完成证据，归为 keep / extend / not_fit，不重复建议新建。未建的机会归为 candidate / watch / not_fit；candidate 表示值得试验的工作机会，不表示已经取得执行权限或平台准入。缺失事实须定向查证；不可得则明确缺口，保留已有工作判断。
4. 内部同时审视成功闭环的复用和“补一小步”的机会，不强求发现。正文只保留通过增量价值门禁的0–3项，按可减少的人工操作/接力与完善成本排序。不输出正常运行清单，不重复列无变化的排除理由；无新机会时一句话即可，必要时点明最关键的限制。
5. 对通过增量价值门禁的每项机会，用紧凑形式写清：具体工作与 evidence；现在 agent 做了什么、人还做什么；哪些人工判断必须保留；能自主完成到哪一个可验证结果；已有能力/owner；最小缺口或改动；预期省掉的人工操作/接力（无测量不编造耗时）；trigger、精确输入包、输出、terminal oracle、acceptance、authority boundary、human checkpoint；合适载体及理由；最小实验与 keep / extend / candidate / watch / not_fit。重点回答“为什么现在值得自动做、补什么就能做、怎样知道完成”，避免只复述风险。
6. RS / Kimi / DS 执行适配时，完整读取 `/Users/example/Documents/me/<maintenance-checkout>/skills/coding-conventions/patterns/event-admitted-bounded-agent-run.md`，作为该执行路线 automation fit、hard gate、owner boundary 的唯一事实源。文件缺失则该路线的 gate/准入为 unknown，并报告 exact 缺口；仍完成步骤 1–5，不用替代规则伪造该路线准入。
7. 自动化机会只分析并提出实验，不调用执行 agent、不创建 automation/任务、不执行批处理或远端写入。盲测 Run 只按「改动项的验证与落地」创建。机会、实验和 ready 判断都不授予 dispatch 权限。优先复用已有确认工作单，不生成平行任务。

## 改动项的验证与落地

用户已授权符合本节范围的改动自主验证并落地，无需逐条批准。规则与模型配置用盲测验证；本地工具源码按下述工程验证执行。用户只处理排除项。盲测的 spec 格式、判定规则和目录见 `/Users/example/Documents/me/<maintenance-checkout>/docs/runbook/rule-eval.md`。

适用范围：

- l3 仓库中 skill、reference 或 tool-route 的文本。这些文件经软链发布，本地 commit 后即生效。
- automation 的 `model` 或 `reasoning_effort`。
- l3 项目的本地工具源码，以及修复所需的测试和说明。仅修复已核实的摩擦，不接管业务功能开发。

以下是排除项，写入「需要你决定」：

- push、MR 及其他远端写入；生产操作；文件或目录删除。
- 全局 `instructions.md`。
- 放宽生产写入的停止条件、dry-run 或确认步骤。
- 新增开关、配置项或流程步骤，或删除现有功能。
- 非 l3 仓库的改动；目标文件在工作区已有未提交改动的改动。
- 无法冻结成场景的规则或模型配置改动；缺少可执行验收的源码改动。

排除项能冻结成场景时，同样按下面的流程提交和收取盲测，但不落地，结果附在「需要你决定」里。目标是全局 `instructions.md` 时，target agent 启动时已加载当前版全文，verdict 无效。这时只附不加载全局规则的 agent 的逐节点结果，并注明这一限制。哪些 agent 加载全局规则，见 rule-eval runbook 的「边界」。

本地工具源码修复：遵循目标项目的 AGENTS、coding-conventions 和工程检查。先绑定源码身份、`gitlab.flow=l3`、干净目标文件与原失败点。用复现或独立检查证明缺陷，再实施最小修复。运行覆盖原失败点、主路径及最大真实风险的适用测试，不能用选择题盲测代替代码验收。

通过后只 stage 目标文件，本地 commit，并读回提交范围。失败时保留证据与未完成状态，不关闭摩擦。涉及运行实例时核对 freshness；缺重启授权或无法确认加载时标记 `runtime_reload_ready`，不宣称运行摩擦已解决。

规则与模型配置的盲测流程：

1. 冻结场景：从 exact rollout 取关键选择点之前的输入，包括用户请求、当时加载的规则片段和工具输出。删去之后的用户纠正，去掉凭据和个人信息。每个场景给 2–4 个选项，在 spec 中写定预期选项。至少 1 个场景是留出场景，即不来自改动草案取材的案例。
2. 提交：运行 `~/.ai/scripts/rule-eval start <spec>`，在 memory 记下输出的 run 目录。Run 是异步的，本轮不等待。
3. 收取：下一轮运行 `~/.ai/scripts/rule-eval collect <run 目录>`。
   - `pass`：按改动草案实施并读回。git 仓库只 stage 目标文件，本地 commit；automation.toml 改动前先备份到 run 目录。日报写明 commit 或备份路径和回退方法。`SKILL.md` 改动随后按「Skill verification trace」登记。
   - `fail`：可以修改草案后重跑一次。第 2 次仍为 `fail` 时判为已否定，在日志写一行，从 memory 删除。
   - `split`：target agent 改善，但其他 agent 退化，说明规则只适合部分客户端。不落地，不重跑，也不判为否定。写入「需要你决定」：列出改善和退化的 agent，并提议只向适合的客户端或模型下发该规则，例如用按模型注入的 hook。
   - `inconclusive`：重跑一次；仍不能判定时转为排除项。
   - `no_change`：基线版已全部选对，改动没有可测收益。不落地，在日志写一行，从 memory 删除。
   - `pending`：保持记录，下一轮再收取。

   提权被拒、commit 失败或读回不一致时，不改用其他写入方式。把改动草案、可直接执行的命令和结果文件路径写入「需要你决定」。
4. 场景保留在 spec 目录。之后修改同一 owner 时，新 spec 带上已有场景；已有场景退化时判为 `fail`。

## Audit / LL review sidecar

Audit 是每次必须完成的独立结算 sidecar，不是日报主题生成器。完整读取并遵守：

- `/Users/example/Documents/me/<maintenance-checkout>/skills/save-context/references/agent-audit.md`
- `/Users/example/Documents/me/<maintenance-checkout>/skills/save-context/references/agent-audit-worker.md`
- `/Users/example/Documents/me/<maintenance-checkout>/skills/loop-ledger/references/closeout.md`

执行边界（待结算 receipt 以事实包 `audit_receipts_unsettled` 为准）：

1. 对事实包列出的每个 receipt 最多调用一次 `save-context-audit-rs status --receipt <exact-path>`，不等待、不轮询、不读 Run trace。
2. pending 保留 exact run/receipt/output。pending 时长按 `receipt.json` 的修改时间计算。超过 7 天的 receipt 写入「需要你决定」一次，写明 exact receipt、owner 和两个选择：“取消 run 后按 reference discard”或“继续等待”。之后状态不变不再报告。ready 才读取 `agent-audit.yaml`，并以 recovery packet 与 effective LL 验证每个 candidate。
3. 既存 durable fix+anchor 为 resolved；正常、不可复现或证据不足为 ignored；达到 reference 门槛才按 exact signature promoted/deferred。settlement 不表示修复已实施。
4. 可结算 receipt 生成完整 `save-context.audit-settlement.v1` 并 settle；terminal failed 且 helper 返回 `needs_discard=true` 时按 reference discard。每个 candidate exactly once。
5. Audit 结算只写/合并 `~/.ai/agent-frictions.md` 与 settlement/discard artifacts。结算本身不授权修复。选中的摩擦另按「Open 摩擦修复」和「改动项的验证与落地」执行。不改项目 backlog、active FF/LL，不 prune/delete workspace、不建任务、不触发远端写入。
6. 各状态与各 lane 的汇总只写入日报日志；Audit finding 只有通过“行为机制建议准入门禁”才能影响主建议。

## Open 摩擦修复

每轮在 Audit 结算后检查 Open 摩擦，包括历史存量。此流程独立于前一日是否有人工作。旧条目未关闭且具备修复条件，就进入执行候选，不因“没有新 occurrence”或“没有新建议”跳过。

1. 运行 `~/.ai/scripts/agent-frictions open-summary`。摘要只显示部分条目时，读取 `~/.ai/agent-frictions.md` 的 Open 标题与 signature，再按影响和可执行性选择。只展开选中条目的证据与 owner，不把摘要显示数当成总数。
2. 回读原失败点和当前实现。已有修复时验证原失败点，避免重复实施。仍存在时准备 exact 文件、最小 diff 和验收命令。局部工具修复不要求跨 case 证据，也不要求先换模型；跨项目行为规则仍遵守原准入。
3. 按「改动项的验证与落地」自主修复。与其他来源共用每轮最多 3 个改动项，不另加配额。遇到排除项或并发改动时保留具体阻塞，继续其他可执行项，不停在统计或泛化建议。
4. 修复通过并完成本地提交后，按摩擦台账现有规则关闭 exact signature。保留修复提交、原失败点验收和必要运行读回证据。默认入口改变时同步原 tool-route，规则文本仍走盲测。未确认生效的 runtime 修复保留 Open。禁止以 ignored、expired、测试无关或已有补丁为由冒充修复完成。
5. 日报写出本轮修复、验证、提交、回退方式及未完成原因。数量以写后 `open-summary` 读回为准。历史摩擦不因建议满 14 天自动关闭。

## Automation memory hygiene

1. 完整读取 `/Users/example/Documents/me/<maintenance-checkout>/skills/agent-doc-hygiene/SKILL.md` 与 `references/layer-rules.md`。
2. 枚举 `$CODEX_HOME/automations/*/automation.toml` 与 memory.md，只纳入 ACTIVE，排除 PAUSED 与三个 agent-forum；无 memory 跳过。
3. memory 只保留 Doing、Blocked、Next Steps、必要 Critical Context、durable pointers、影响下次运行的最近结果及无 durable owner 的未完成事实。
4. 超过 8 KB、80 行，或存在明显 chronology、重复 readback、已完成发布、过期历史、陈旧临时路径、重复规则时才进入 cleanup；每次最多 2 个。
5. 改写其他 automation 的 memory 前，证明它未运行。本 automation 的 memory 由本轮最后一步整理，不计入第 4 条的 2 个名额。运行记录只保留最近一次，替换旧行。有当日日报时，本轮记录写入日报日志。其余内容只保留第 3 条所列项目，并适用第 4 条阈值。保留未完成工作、阻塞、有效决策、remote IDs/URLs 与恢复 anchors。
6. 一次性改写为 Current State / Doing / Blocked / Next Steps / Critical Context / Relevant Durable Pointers；不建备份、不删文件、不改 prompt/schedule/status、不触发远端写入。读回并报告 before→after bytes/lines。

## 输出

中文。主分析完成后，先写日报文件，再执行 Audit sidecar、Open 摩擦修复、memory hygiene 与 skill verification，并把结果追加到日报日志。运行中断时，已得出的结论不丢失。

### 改动项

改动项必须同时具备以下 3 项，缺任一项的条目只写日志：

- owner：要改的 exact 文件或配置路径。
- 改动草案：可直接应用的 diff、配置值或命令。
- 验收方法：盲测 spec 路径，或检查命令。

每轮最多 3 个改动项，编号 #1–#3。行为、自主交付、Audit 和 Open 摩擦来源的改动项合并排序，按可减少的人工操作或接力排序。适用范围内的改动项按「改动项的验证与落地」处理。排除项写入「需要你决定」，有盲测结果时附上；不每日重提，登记 14 天后按 expired 处理。

### 日报文件

路径为 `/Users/example/Documents/me/_Drafts/<被回顾日期>-daily-work-review.md`，标题为“前一日工作回顾 - YYYY-MM-DD”。文件依次包含以下各节：

1. 需要你决定：排除项、`split` 项和超期 receipt；没有就写“无”。
2. 已自动处理：本轮落地的改动（commit 或备份路径、回退方法）、本轮否定的改动、本轮提交的盲测 Run。没有就省略本节。
3. 日志：本轮新证据与结论变化、观点变化（链接工作观点条目）、expired 项、Audit / hygiene / skill 状态、取材与证据边界。观点最多 2 项，行为建议最多 2 项，自主交付机会最多 3 项。日志不重述旧建议和未变化的实验，通常不超过 1500 中文字。

取材与证据边界写明回顾日期、来源类别，以及深读、抽样和仅查状态的范围。召回数不等于审阅数；只写实际读取的材料。“无新增”只描述本轮，不代表机制有效或旧问题已解决。

没有已自动处理项、决策项、观点变化或需保留的证据边界时，不建文件。同日重跑沿用原文件，只更新本轮变化。

### 最终回复

先列需要你决定的项；没有就写“无需决定”。再列本轮落地的改动，每条一句话，附回退方法。最后用一句话说明本轮取材。

确认无人工作且没有修复结果或决策项时以 NO_FINDINGS 开头。最终回复不复述观点正文、pending、正常运行清单或未变化的来源限制。每周一的运行另附过去 7 天变化的观点编号，每条一句话。遵守宿主要求的 inbox directive；inbox 摘要只写需要你决定的项和本轮落地的改动。

### automation memory

只保留以下内容：

- 未关闭的待验证策略、试验和机会，含登记日期；已提交的盲测写明 run 目录。
- 触发条件与去重所需最小结论。
- 观点笔记指针与 durable pointers。
- 最近一次运行的时间与结果，一行，替换旧行。

已有 durable owner 的历史不复制。无新增不等于清除未完成事项；下次只在新证据、状态或条件变化时重新展开。

## Skill verification trace

1. 只消费事实包 `skill_verification`：它列出 open 记录，即最新登记、内容未漂移且尚无静态检查的记录。不另行调用 status，不扫描或修改原始 ledger。
2. 按 `change_id` 与本 automation memory 中上一轮状态比较，只报告新出现的 open 记录。同一条不重复报告。无变化保持安静。
3. `static_validated` 是默认完成状态，只表示静态检查或 RS 实验通过，不得写成真实行为已验证。不追踪待采样项。
4. 自动化只读消费，不执行 `begin`、`check`、`load` 或 `sample`，也不因 ledger 状态获得源码修改、restart 或远端写入权限。例外：本 automation 按「改动项的验证与落地」落地的 `SKILL.md` 改动，改完后执行 `begin`，再用盲测结果文件 `check`。

## 收尾必做事项核对

事实包 `obligations` 列出确定性可核对的收尾必做事项缺口；当前只有一项：会话在窗口内用 apply_patch 修改 `SKILL.md`，同一会话却没有 `skill-verification begin`。

1. 逐条回读对应 rollout 片段，确认修改属实且不是被撤回的草稿，再判断是否构成执行缺口；`limitations` 中未覆盖的修改方式不得推定为合规。
2. 成立的缺口进入行为机制分析的“已有机制未生效”路径，按原 owner 局部处置；同一会话同一 skill 只报告一次。
3. 只报告和建议，不代为执行 `begin`。
