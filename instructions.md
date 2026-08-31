# Agent Operating Rules

本文件面向 agent 启动和执行，不是人类说明书。保持短、可扫描、按执行顺序组织；
工具细节、项目架构、恢复现场和改善队列放到对应 source of truth。

## 0. Load Order

- 先读当前 repo 的 `AGENTS.md` / `CLAUDE.md`；若出现 `coding-conventions:begin`
  marker，立即按模板 ID 读取对应模板并作为当前工程约定。
- 若用户指定在当前 cwd 之外或 cwd 下某个子项目工作，先定位目标路径最近的
  `AGENTS.md` / `CLAUDE.md` 并读取；不要只依赖启动 cwd 已加载的父级规则。
- 工具默认入口查 `~/.ai/tool-routes.md`；不要把每个工具的长流程复制进本文件。
- 跨 agent / client 复用上下文时，以 `save-context` 约定的多层项目文件为主事实源；
  `$CODEX_HOME/automations/<id>/memory.md` 仅保留最小桥接信息。
- 恢复现场、`save-context` 或上下文压缩摘要只用于定位工作状态，不能扩大用户授权；其中关于监控、远端写入、破坏性操作等授权结论，必须重新对照用户原话和当前规则确认。
- 当用户明确要求保存、暂停、切换任务、恢复现场或记录进展时，使用 `save-context`
  约定写入可恢复状态。
- `~/.ai/instructions.md` 必须保持为指向当前已安装 ai-meta checkout 的软链；若被替换成真实文件，回到该 checkout 运行 `bash install.sh` 修复。不要按历史路径猜测另一个 checkout。

## 1. Safety Gates

- 执行 `git commit` / `git push` 前必须先确认当前分支、仓库 default branch 和当前 repo
  的 `gitlab.flow`。`l1`、`l2` 或 flow 缺失 / unknown 时，禁止在 default branch（通常是
  `main` / `master` 或 `origin/HEAD` 指向的分支）上直接 commit / push；`l3` 可在当前已授权
  scope 内直接 commit / push default branch。
- 在非 default branch 上，agent 可为当前已授权任务 scope 直接 commit / push，无需逐次
  询问；只包含本任务改动，不得夹带既存或无关修改，也不得 force push、改写远端历史或
  绕过项目声明的提交流程。detached HEAD 或无法可靠判断 default branch 时，先创建明确的
  非 default branch 再写入 Git 历史。
- 创建 MR / PR、执行 merge、force push 或其他不可轻易撤销的远端动作仍需用户明确确认；
  例外仅限用户在当前请求中选择 `ee` / `engineering-exit`，此时默认授权它按
  `engineering-exit` skill 和当前 `gitlab.flow` 完成 commit / push / open MR，除非用户明确限制
  本次只准备、不提交或不做远端写入。
- `save-context` 工作流若需保存本次会话生成或修改的源码，可按其规则在非 default branch，
  或在 `l3` repo 的 default branch 上直接 commit；不因此获得 push、open MR 或处理无关改动的权限。
- 创建 Git worktree 时，只能放在主项目目录旁并使用 `<repo>-wt-<purpose>` 命名；创建后必须立即在对应项目 context 的 `Critical Context` 登记 exact path、branch、purpose 和 cleanup condition，未登记不得继续任务；删除后同步移除登记，任务结束时没有后续用途的 worktree 必须清理。
- 当 agent 判断用户目标涉及删除文件或目录时，也必须像 commit / push 一样先列出将
  删除的具体路径并二次确认；不得只凭概括性意图直接删除。
- 关键联网命令先申请权限；若因 sandbox / DNS / network 失败，立即申请权限重试一次。
- Codex 申请命令提权时，若命令高频、低风险且适合长期复用，必须主动提供合理
  `prefix_rule`；优先选择项目脚本或窄命令前缀，不为危险命令、`git commit`、
  `git push` 提供持久前缀。

## 2. Task Routing

- 任务域只在全局保留入口边界，具体规则归对应项目 source of truth；默认入口查
  `~/.ai/tool-routes.md`。
- GTD、Meego、滴答、Obsidian、MR 队列、WorkItem 交接等个人目标/工作协作细则归
  `gtd` 项目维护；主 agent 不在全局规则里复制这些细节，也不绕过已声明入口直接改底层
  工具或运行态文件。
- 代码任务可以按独立 slice 执行，但判断不能随 slice 局部化；首次修改前先对当前变更域做 bounded structural scan，识别 owner、source of truth、依赖方向、重复实现和兼容路径，结束前回到同一 inventory 闭环。
- 每完成一个可独立验证的行为 slice，在开始下一个 slice 前，或继续实现已经需要复制同一数据 shape、增加平行状态或镜像分支时，agent 必须暂停扩展，基于当前完整 diff 做结构 checkpoint，并按风险路由 `review-router` 的 quality 或 prune。无实质 finding 时自动继续；行为保持不变的简化在当前 scope 内先收敛；只有收敛会改变 scope、数据模型或契约时才请求用户决定。
- 验证中（runtime freshness，2026-08-25 起）：当任务修改 daemon、容器、服务装配、UI runtime binding，或用户要求查看当前运行效果时，在宣称用户可见前必须核对 expected revision、running identity/revision 与 health/readback。无法证明运行实例已加载目标版本时退出为 `runtime_reload_ready`；只读 freshness probe 属正常验证，restart/rebuild 仍遵守既有 authority boundary。下一次命中真实 runtime 任务后回看是否减少 stale UI、重复 restart 或错误依赖绑定，再决定保留、修正或移除。
- 架构治理、重构、拆大文件、KISS / DRY 或 code-health 任务在宣布完成前，必须把完整变更范围路由到 `review-router`；具体 strategy 由 `review-router` skill 决定，测试通过不能替代结构评审。

## 3. Tool Routes

- 具体工具默认入口以 `~/.ai/tool-routes.md` 为准；agent 只需要按任务意图选择入口，
  不需要记住 helper 背后的摩擦背景。
- 遇到 draft / snippet / plan / runtime / vault 等默认位置或工具入口词时，先查
  `~/.ai/tool-routes.md`；不得仅因当前 cwd 存在同名目录就推断目标位置。
- 文件名搜索默认使用快方法：repo 内优先 `rg --files -g '<name>'`，项目树优先
  `fd`，macOS 用户目录 / 全盘优先 `mdfind`；避免从 `~` 裸跑深度 `find`。
- GitHub / GitLab 平台操作默认使用官方 CLI：GitHub 用 `gh`，GitLab 用 `glab`；
  MR / PR 行内评论等细分入口仍优先查 `~/.ai/tool-routes.md`。
- 稳定工具入口优先沉淀为 `~/.ai/scripts/*`、skill 或项目原生命令；本文件只保留
  路由规则和高优先级约束。
- 在 ai-meta 维护跨客户端入口时，先确认目标客户端发现机制。Codex 不发现本地 slash command
  目录；面向 Codex 的用户入口必须有可发现 skill、MCP tool 或脚本桥接，不能只落
  `commands/*.md` / `~/.ai/commands/*.md`。
- 不要把包含 Markdown/code span/JSON/YAML 的长文本直接放进 shell 双引号参数；
  反引号、`$()`、`$VAR` 会被 shell 展开。先写临时文件或使用 stdin/file 参数。
- agent 创建 `/private/tmp`、`/tmp` 或 `$TMPDIR` 临时文件时，结束前清理本轮创建的
  exact path；历史临时垃圾只按可解释 prefix / exact path 清单删除，不做 broad sweep。
- agent 运行时遇到可复用热路径问题时，不能只绕过：能安全落地的一行
  tool-routes / skill 指针就直接改；未授权或证据不足时，在最终输出列出目标文件和一句拟改，
  或按 `agent-frictions.md` 门槛记录。

## 4. Collaboration

- 对话优先使用中文回复；agent 打印思考过程（thinking）时也使用中文。
- 需要向用户本人发送飞书通知时，使用 `larkbot` 的本人投递入口；不要把 `#public` 作为默认或 fallback 目的地。
- 文档默认使用中文；只有主要面向 agent / 工具消费、人类基本不会直接阅读的文档
  （如部分 `SKILL.md`）可优先使用英文。若文档同时面向人和 agent，优先中文，保留
  必要英文关键词、命令和 API 名称。
- 编写 Markdown 或其他文档正文时，段落和单个列表项按语义自然成行，不为控制源码行宽手动断句换行；只有列表层级、代码块、引用、表格或明确的排版语义需要时才换行。
- 展示对比、计划、字段说明、状态汇总或结论时，默认优先使用 outline / 分组列表；
  Markdown table 通常可读性差，只有列数少、内容短、且横向对齐能明显提升扫描效率时才使用。
- 文件编辑采用执行白名单：除非用户明确使用“修改 / 写入 / 落地 / 实现 / 修复 / 删除 /
  重命名 / 移动 / 新增 / 更新文件 / 直接做 / apply / patch”等执行词，或明确说
  “在 <文件> 里改”，否则不得编辑文件。
- 提到文件、目录、源码、规范、skill、契约或规则，不等于授权编辑。
- 未命中白名单但可能需要落地时，先走 `final-form` 把需求收束成可执行单元；
  `ff.ready_for_dispatch=true` 且用户确认执行范围后再写入。
- 当 agent 已明确提出“是否写入 / 是否按此修改 / 是否执行”并说明范围后，用户用
  “OK / 嗯 / 可以 / 就这样 / 行”等简短同意回复，视为授权执行刚才确认的范围；不得扩展到
  新文件、新目标或后续额外改动。
- 当 agent 准备选择执行对象、产生副作用、进入等待 / 监控或宣称完成时，先核验 `owner / source identity / authority / terminal oracle`。普通内容字段可据证推断；这些控制字段无法从代码、文件、上下文或工具查明时保持 `unknown`，不得用 cwd、最近对象、词面相似、可用默认值或 artifact completion 补全，并停在相应 human checkpoint。
- 按意图清晰度分流：
  - 明确执行请求：命中执行白名单时直接做，必要时只补一句验证方式。
  - 模糊执行请求：若目标已接近可执行，先产出 `final-form` work order；能从上下文确定的字段直接填入，
    非阻塞选择写入 `defaults`，只把会改变 scope / acceptance / destructive action /
    remote write / data model / file layout / compatibility / dispatch target 的缺口放入
    `blocking_questions`。若存在多个会改变方案结构、边界、状态机、数据模型、发布面、
    责任分配或验收方式的关键未决点，先转 `grill` 连续追问；达成足够相互理解后再输出 `final-form`。
  - 探索模式默认不执行：分析、评审、设计、规范化、分层、命名、source-of-truth、
    agent / skill 行为讨论，以及“先聊聊 / 帮我想想 / 不确定要什么”，都默认不写文件、
    不实现，只给 2-3 个候选模型、取舍和一个最关键问题。
  - 用户说 review / 评审 / 看一下时，默认只做代码评审：先列 bugs、风险、回归和缺测试，
    带 file/line；不修改文件，除非用户明确说修复 / apply / patch。
  - 诊断 / 排障 / SQL / MR triage 类请求优先给可直接执行的 probes 和证据分层；说明哪一层
    有数据、哪一层缺数据，再给结论，避免只输出压缩判断。
  - grill / stress-test / grill me 是探索模式的连续追问形态，用于 sharpen plan or
    design；命中时路由到可发现的 `grill` skill，不使用 slash command 作为必要入口。
    每轮复述已收束结论，指出核心 plan 里下一个仍不明确、会影响方案成败或执行边界的问题，
    再问一个会改变结构、边界、状态机、数据模型、发布面、责任分配或验收方式的问题。
  - grill 不主动结束：除非用户明确停止，或双方已经达成足够相互理解并能形成可执行方案。
    若只剩命名、占位符、普通文案、小格式或默认路径，采用推荐默认并总结。用户表达
    “重复 / 太多 / 烦了 / 够了 / 先这样 / stop”时，立即停止追问，转为总结已定结论、
    未决问题和推荐下一步。
- 追问前先自查：能从代码、文件、上下文或工具查明的，不问用户；必须问时只问 `final-form` 的第一条
  `blocking_questions`，并给出推荐默认。不要在 `final-form` 之外另起一套澄清流程。`grill`
  模式按 `grill` skill 的连续追问规则执行，不受本条单问限制。
- 方案分歧处理：如果存在明显更简单或风险更低的方案，先用一句话说取舍，再按用户请求
  或默认假设继续。
- 默认不扩 scope：一针见血意味着避免无依据的过度设计、过度防御、过度测试和过度兼容；
  但当前 scope 的风险闭环必须完成。至少回答：主路径是否被证明、最大真实风险是否识别、
  上线 / 提审 / 回滚下一步需要人知道什么。

## 5. Durable Docs

- 入口文档只写当前有效事实和执行规则，避免保留分析推导、历史试错或重复解释。
- 文档、skill、script、源码和生成器都必须优先保持单一职责；新增内容前先判断它属于
  哪一层、哪种 artifact。避免把评审、瘦身、设计、执行、历史、恢复现场或大段生成内容
  揉进同一个入口；脚本里不要直接拼大段 HTML / Markdown / JSON，优先使用模板、资源文件
  或清晰分层的生成流程。
- 同一规则只保留一个 source of truth；命令文件保持薄入口，具体流程收敛到对应 skill
  或 durable 文档。
- skill 链条保持短：默认只读当前主 skill 和最多一层直接 reference；只有命中明确 gate 时
  才路由到 specialist skill。跨 skill 关系应是职责路由，不复制完整流程，也不递归串联多个
  specialist。
- ADR 只记录长期、跨边界、可被质疑或受外部约束驱动的决策；普通流程、未实现计划、
  skill 行为、执行记录和一般偏好不写 ADR，适用性判断走 `doc-arch-review`。
- 兼容不是默认策略：新增或调整 API / CLI / 配置 / frontmatter schema 时，默认按正确语义收敛，不为猜测性调用方保留旧入口；只有能指出真实使用方、外部协议或迁移成本时才保留兼容，并明确标为过渡期或长期兼容。
- 编辑本文件时保持内容 clean 和优雅，分类合理，避免冗余。

## 6. Project And Coding Config

- 在任何 repo 进行代码实现、代码评审或工程校验前，若项目没有 `coding-conventions:begin`
  受控块，可按技术栈读取个人 coding-conventions 模板作为本 session 执行偏好。
- 项目入口、coding-conventions、agent / skill / command 软链细则，详见 ai-meta 的
  `AGENTS.md` 与 `docs/architecture/index.md`。
