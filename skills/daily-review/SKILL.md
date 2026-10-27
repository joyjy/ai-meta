---
name: daily-review
description: "每日前一日工作回顾与机制改进收口：由 Codex 定时任务调用，先运行 daily-review-collect 取得确定性事实包，再做行为机制、自主交付与观点分析，并完成 Audit / LL 结算、automation memory hygiene 与 skill 验证状态汇报。"
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

同一 signature、同一建议换场景重述、仅增加 recurrence、已有自动化正常运行、规则已修改但无新行为样本、仍缺同一个文件或仍 pending，都不算实质新增。已实施的建议只验证效果，不再次建议实施；“已经修改”仅关闭实施项，不能自动关闭效果判断，须核对修改是否作用于原失败点。去重按下一步是否变化，不按问题是否见过；同一问题出现有直接证据的新失败原因、修复位置或可区分的验证办法，才重新展开，不能仅因增加一次 occurrence 重报。尚未执行且条件未变的实验不每天重提；无匹配样本保持 inconclusive，留在 memory 等触发。

取证和内部判断仍须完成；输出长度取决于值得处理的信息，不为填栏目、满足数量或篇幅配额扩写。三个分析维度分别裁决，允许全部无新增；没有纠偏或自动化机会时，仍可有值得报告的新观点。不得为追求新颖而扩大扫描范围、降低证据门槛或虚构用户成本。

## 前置硬门禁

1. 先做最小取材，判断前一日是否至少有一项“人主动发起且发生实际推进、交付或决策”的工作。automation、自主后台维护、审批/权限子任务、context 加载/恢复、无副作用定时跳过不算人工工作。
2. 无论是否有人工作，每次运行都完成独立 Audit / LL review 收口。
3. 若足以确认无人工作：跳过行为机制分析、daily-work-review 文件与 memory hygiene，但继续 Audit/LL；无需人处理只返回 `NO_FINDINGS`，需人决策只返回 exact audit、owner、最小决策。
4. 关键来源失败或扫描不完整时不得推导无人工作，报告 exact 缺口。
5. wall-clock 跨日、未开机或没有 automation run 不构成 recurrence、噪音或 aging；只按实际 receipt、独立 occurrence 和 status transition 判断。

## 前一日取材边界

1. 先读前一日 Daily Note、相关 project context、automation memory / run receipt。
2. Codex task 历史只走本地只读 date-bound manifest，不调用线程列表工具：
   - 以事实包 `threads` 为召回清单；它按 `created_at_ms < end_ms AND updated_at_ms >= start_ms` 查询 `/Users/example/.codex/state_5.sqlite`，updated 只用于召回；`rollout_found=false` 的条目已记入 `gaps`；
   - 读取 `/Users/example/.codex/sqlite/codex-thread-summaries-dev.db` 对应 summary（存在时），从 exact rollout_path 仅提取窗口内 user/assistant turns、terminal event 与末尾必要上下文；长任务不从头读；
   - 只有 rollout 内有窗口期实际推进/交付证据才纳入；纯 load-context、状态刷新、mtime 或 updated time 不算工作；archived task 同样使用 exact rollout_path。
3. 只读取 turns 自然出现的本地文件、MR/Issue/文档链接作为 anchors，不横扫 repo、GitLab 或原始聊天历史。
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
规则冲突的持续收口：遇到本窗口实际影响选择的冲突时，按 `agent-doc-hygiene` 的冲突检查定向核对当时实际加载的条款、用户纠正和原 owner，不横扫所有规则。分别判断业务事实是否已知、当前有效政策是什么、还缺哪项决定；不得把政策未对齐当成事实未知而让用户重复确认。按全局 instructions 的冲突裁决规则核验当时可继续的授权路径和原验收，既不默认越过停止条件，也不以“按规则停下”结算整个目标。具体修复优先替换旧条款或收窄适用条件，不叠加平行规则；记入 memory 只作桥接。当前业务终态、原 owner 修复/消费者读回、目标版本后的真实行为效果分别结算。本定时回顾仍只提出具体改动和必要授权，不自动修改其他规则或业务配置；用户在后续对话明确批准修复后，沿该范围实施并读回，不继续停在建议或重复确认。下一轮只因修复状态或匹配行为证据变化重新展开，未实施且条件未变不每日重提。

7. **Audit 反证**：最后用 Audit 检查遗漏、反例和合同偏差；不得因 candidate 数量、promoted 或 severity 自动改变主题。
8. **上一轮验证**：对 memory 中实验判定 validated / inconclusive / falsified / superseded；没有新的真实行为证据保持 inconclusive。

## 观点发现


观点的长期来源是 `/Users/example/Documents/me/Resources/工作观点.md`。开始观点分析前读取该笔记，按其中维护约定与已有判断、边界及来源查重。用户已授权本自动化维护这份笔记：仅在本轮真实证据带来实质增量时，更新对应稳定编号条目的证据、判断、适用边界、价值与成熟度或下次观察点；确属不同判断时才新增条目。被推翻或合并的条目保留编号、简短理由及后继指针，不删除。无变化不改日期、不追加每日记录。每日报告只呈现本轮变化并链接该条，automation memory 只留笔记指针和必要待决信息，不复制观点正文。来源缺失时记录限制，不用报告自述提升成熟度；文件读取失败时不得另建平行观点库。本节仅授权维护这份观点笔记，不授权执行实验、派工、新建任务或修改源码、skill、规则。

从同一批真实工作证据中独立寻找观点，不只从错误和用户纠正取材；成功做法、反例、取舍及意外结果同样可用。用自己的判断说明为什么值得注意，不能把所有发现都改写成“补证据、加门禁、更谨慎”，也不为制造新颖而追求反直觉。

每个入选观点用自然语言串起：原来怎么理解（没有证据时只称待检验假设，不虚构大家的共识）→ 哪个真实案例挑战或细化了它 → 新的判断及适用边界 → 以后会因此作出什么不同决定。保留具体业务关系和关键反例，避免抽象成脱离案例的常识口号。

价值与成熟度分开：价值看能改变什么重要判断及潜在适用面；成熟度据证区分单例观察、待验证假设、已在真实场景验证或已有独立复用，不用“有潜力”冒充可靠。一个有证据的单例可以提出有价值的假设，不必先满足行为纠偏的跨case门槛；若进一步建议修改默认规则或自动化执行，仍须分别通过原有准入与权限边界。

只输出0–2个有实质增量的观点；不凑数、不恢复每日论坛/议会/自评流程，不强迫每个观点生成checklist、skill或任务。值得验证时给出最小区分性问题或实验：什么结果会支持、推翻或收窄它；没有必要实验时明确保留为观察即可。已知观点仅在新证据改变判断或适用边界时重提，单纯换案例不算新增。观点与纠偏/自动化机会指向同一发现时合并叙述，不重复计数。

## 行为问题分层处置与机制建议准入门禁

分别裁决问题成立、局部处置和跨项目推广，不用同一个门槛替代三者：

- **具体问题**：一次直接证据即可成立，但须证明它是原目标与授权下的执行缺口，而非后续新增要求。问题重要性不由是否新颖或是否足够推广决定。
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
- 检查前一日 automation 是否有用或产生人工补救；本回顾自身后续收到的纠正与催促，由下一轮按窗口内真实人工跟进纳入同等分析，核对是否在已有目标、授权和可查证据下过早收口，不将用户“继续/试试”视为原本就必须取得的新授权。只提建议，不自动修改其他 automation、项目源码、skill、tool-route、active FF/LL，不创建任务或 Run。

## 自动化与自主交付分析

本节是独立主分析，不是行为纠偏的附录，不受“跨 case 失效或单一高影响错误”准入门槛约束。一次真实成功闭环也可支持复用机会，但不能据此宣称稳定或跨场景可靠。

1. 从昨日代表事项逐项扫描三类机会：已成功自动完成、人工反复做或接力、已授权但尚缺最后交付步骤。优先找“少量完善即可自主完成”的具体工作；不把泛化的更主动、加规则或继续修 bug 当作自动化分析。
2. 对每项先给工作层面的判断，再选择实现载体：无需新增机制、固定脚本/批处理、当前任务自主接续、Codex 定时自动化、事件驱动 RS、其他或 unknown。模型与平台是后续适配项，不预设 Kimi/DS，不因某个平台不可用否定整个机会。只有需要比较 Kimi/DS 时才依据当日可验证能力选择 Kimi / DS / either / unknown。
3. 已有自动化先查其 owner、触发、产出和真实完成证据，归为 keep / extend / not_fit，不重复建议新建。未建的机会归为 candidate / watch / not_fit；candidate 表示值得试验的工作机会，不表示已经取得执行权限或平台准入。缺失事实须定向查证；不可得则明确缺口，保留已有工作判断。
4. 内部同时审视成功闭环的复用和“补一小步”的机会，不强求发现。正文只保留通过增量价值门禁的0–3项，按可减少的人工操作/接力与完善成本排序。不输出正常运行清单，不重复列无变化的排除理由；无新机会时一句话即可，必要时点明最关键的限制。
5. 对通过增量价值门禁的每项机会，用紧凑形式写清：具体工作与 evidence；现在 agent 做了什么、人还做什么；哪些人工判断必须保留；能自主完成到哪一个可验证结果；已有能力/owner；最小缺口或改动；预期省掉的人工操作/接力（无测量不编造耗时）；trigger、精确输入包、输出、terminal oracle、acceptance、authority boundary、human checkpoint；合适载体及理由；最小实验与 keep / extend / candidate / watch / not_fit。重点回答“为什么现在值得自动做、补什么就能做、怎样知道完成”，避免只复述风险。
6. RS / Kimi / DS 执行适配时，完整读取 `/Users/example/Documents/me/<maintenance-checkout>/skills/coding-conventions/patterns/event-admitted-bounded-agent-run.md`，作为该执行路线 automation fit、hard gate、owner boundary 的唯一事实源。文件缺失则该路线的 gate/准入为 unknown，并报告 exact 缺口；仍完成步骤 1–5，不用替代规则伪造该路线准入。
7. 本回顾只分析并提出实验，不调用执行 agent、不创建 automation/任务/Run、不执行批处理或远端写入。机会、实验和 ready 判断都不授予 dispatch 权限。优先复用已有确认工作单，不生成平行任务。

## Audit / LL review sidecar

Audit 是每次必须完成的独立结算 sidecar，不是日报主题生成器。完整读取并遵守：

- `/Users/example/Documents/me/<maintenance-checkout>/skills/save-context/references/agent-audit.md`
- `/Users/example/Documents/me/<maintenance-checkout>/skills/save-context/references/agent-audit-worker.md`
- `/Users/example/Documents/me/<maintenance-checkout>/skills/loop-ledger/references/closeout.md`

执行边界（待结算 receipt 以事实包 `audit_receipts_unsettled` 为准）：

1. 对事实包列出的每个 receipt 最多调用一次 `save-context-audit-rs status --receipt <exact-path>`，不等待、不轮询、不读 Run trace。
2. pending 保留 exact run/receipt/output。ready 才读取 `agent-audit.yaml`，并以 recovery packet 与 effective LL 验证每个 candidate。
3. 既存 durable fix+anchor 为 resolved；正常、不可复现或证据不足为 ignored；达到 reference 门槛才按 exact signature promoted/deferred。settlement 不表示修复已实施。
4. 可结算 receipt 生成完整 `save-context.audit-settlement.v1` 并 settle；terminal failed 且 helper 返回 `needs_discard=true` 时按 reference discard。每个 candidate exactly once。
5. 仅允许写/合并 `~/.ai/agent-frictions.md` 与 settlement/discard artifacts；不改源码、skill、tool-route、项目 backlog、active FF/LL，不 prune/delete workspace、不建任务、不触发远端写入。
6. 汇总 pending / ready / settled / discarded / needs_human 与各 lane；Audit finding 只有通过“行为机制建议准入门禁”才能影响主建议。

## Automation memory hygiene

1. 完整读取 `/Users/example/Documents/me/<maintenance-checkout>/skills/agent-doc-hygiene/SKILL.md` 与 `references/layer-rules.md`。
2. 枚举 `$CODEX_HOME/automations/*/automation.toml` 与 memory.md，只纳入 ACTIVE，排除 PAUSED 与三个 agent-forum；无 memory 跳过。
3. memory 只保留 Doing、Blocked、Next Steps、必要 Critical Context、durable pointers、影响下次运行的最近结果及无 durable owner 的未完成事实。
4. 超过 8 KB、80 行，或存在明显 chronology、重复 readback、已完成发布、过期历史、陈旧临时路径、重复规则时才进入 cleanup；每次最多 2 个。
5. 改写前证明 automation 未运行；不得清理本次运行中的自身 memory。保留未完成工作、阻塞、有效决策、remote IDs/URLs 与恢复 anchors。
6. 一次性改写为 Current State / Doing / Blocked / Next Steps / Critical Context / Relevant Durable Pointers；不建备份、不删文件、不改 prompt/schedule/status、不触发远端写入。读回并报告 before→after bytes/lines。

## 输出

中文，按增量分为两种输出，不再强制固定栏目、代表事项数量或自动化分析篇幅占比。

最终回复须用一小段“本轮取材”概括实际读了什么：回顾日期、主要工作主题、来源类别（如 Daily Note、相关 project context、窗口内任务记录、既有观点及机制 owner）；有可靠计数时可简列召回与实际读取数量。区分深读、抽样和仅查状态，不把召回数当作全部审阅数，不逐条堆文件名或工具流水。只报告实际读取的材料；影响结论的关键未覆盖或读取失败简短说明。取材摘要无论有无新增都保留；确认无人工作时，仍以 NO_FINDINGS 开头并附最小取材依据，此要求替代前置门禁中“只返回”的字面限制。

“无新增建议”只描述本轮增量，不代表工作流成熟、已有问题解决或机制有效；若有重要执行缺口但尚无可靠改法，简短说明 exact 证据缺口或待区分假设，不重述未变化历史，也不为证明不成熟而凑发现。

用一句话交代三个分析维度各自的裁决；无新增维度可附最关键的一条依据，避免让“未展开”看起来像“未检查”。不重述旧建议、正常运行清单或未变化实验。取材与裁决摘要不算新增发现，不因此生成完整报告或扩大扫描范围。

**无实质新增：** 即使昨日有人工工作，也只简短返回“本轮无值得处理的新发现”，必要时补一条影响结论的来源缺口，以及一行 Audit / hygiene 状态。不得复述昨日工作、已知原则、旧建议或未变化实验；不生成完整 daily-work-review。若需保留证据边界，在 `/Users/example/Documents/me/_Drafts/<被回顾日期>-daily-work-review.md` 写不超过300中文字的运行记录（窗口、扫描数量、关键缺口、无新增结论及必要新anchor）。没有记录需要则不新建文件。同日重跑沿用原文件，不覆盖丢失已记录的有效结论，仅更新本轮增量或无新增状态。无人工作仍按前置 NO_FINDINGS / exact audit 特例。

**有实质新增：** 写入同一日期的 daily-work-review.md，标题为“前一日工作回顾：新增发现 - YYYY-MM-DD”。正文通常800–1500中文字，信息少则更短；Audit需人决策的exact明细可以单独附后。只写：
- 本轮新证据与结论变化；每项连接具体工作及其改变的理解、决定或用户成本，避免重述完整历史。
- 值得学习或试验的新观点最多2项，分别说明价值与成熟度，不强制变成改动建议；行为建议（局部修复、对照试验及跨项目修订合计）最多2项、自主交付机会最多3项，允许任一维度为0。同一发现合并叙述，保留各自准入要求，不机械展开模板。
- 需要用户处理的下一步最多3条；优先收益明确、缺口最小的机会，未获执行授权只提实验，不创建任务。
- 末尾简列 evidence boundary / anchors、Audit与hygiene状态。

最终回复先给结论，有文件则附绝对路径；只展开新发现及其具体价值，通常300中文字以内。无变化的来源限制、平台缺口、pending与实验不得每天重述；需要人处理的Audit即使主分析无新增也必须给exact audit、owner和最小决策。审计不能拿来填主分析内容。遵守宿主要求的 inbox directive。

automation memory 只保留待验证策略、机会的待决缺口、观点笔记指针及必要待决信息、实验、触发条件、去重所需最小结论与durable pointers；记录本轮有无增量和当前运行时间。已有durable owner的历史不复制。无新增不是清除未完成事项；下次仅在新证据、状态或条件变化时重新展开。

## Skill verification trace

1. 只消费事实包 `skill_verification`：它列出全部 open（pending / inconclusive）记录，并带 `source_drift`（登记后已改动的 artifact）与 `superseded_by`（同一 SKILL.md 更新的记录）。不另行调用 status，不扫描或修改原始 ledger。
2. 按 `change_id` 与本 automation memory 中上一轮状态比较，只报告新记录、verdict / evidence count 的变化，以及新出现的过期记录：`source_drift` 非空的记录不能再取得 `validated`，报告需要重新登记或停止追踪；仅 `superseded_by` 非空时只提示已有更新登记，不判为失效。同一条不重复报告。无变化保持安静。
3. `static_validated` 只表示静态检查通过，不得写成真实行为已验证；`pending` / `inconclusive` 保持待采样，`falsified` 进入机制复查，只有 matching load fingerprint 后达到声明样本数才能判 `validated`。
4. 自动化只读消费，不执行 `begin`、`check`、`load` 或 `sample`，也不因 ledger 状态获得源码修改、restart 或远端写入权限。

## 收尾必做事项核对

事实包 `obligations` 列出确定性可核对的收尾必做事项缺口；当前只有一项：会话在窗口内用 apply_patch 修改 `SKILL.md`，同一会话却没有 `skill-verification begin`。

1. 逐条回读对应 rollout 片段，确认修改属实且不是被撤回的草稿，再判断是否构成执行缺口；`limitations` 中未覆盖的修改方式不得推定为合规。
2. 成立的缺口进入行为机制分析的“已有机制未生效”路径，按原 owner 局部处置；同一会话同一 skill 只报告一次。
3. 只报告和建议，不代为执行 `begin`。
