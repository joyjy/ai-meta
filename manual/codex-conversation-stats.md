# Codex 用户短句统计

`codex_phrase_stats.py` 只读本机 Codex 的 `state_5.sqlite` 和它指向的会话 JSONL，不调用模型或网络，不修改历史。结果默认保存在 `~/.codex/analysis/phrase-results.json`，包含全部短句分组、全部原话及次数、每种原话的一条来源、扫描范围和缺口；Top 10 只限制终端展示，不截断结果文件。再次运行会覆盖指定结果文件。

## 运行

从 ai-meta 仓库根目录执行；只提交脚本、测试和说明，历史日志与统计 JSON 不入库。

```sh
python3 scripts/codex_phrase_stats.py
python3 scripts/codex_phrase_stats.py --since 2026-09-01 --until 2026-09-14 --top 30
python3 scripts/codex_phrase_stats.py --max-chars 50 --threshold 0.90 --output ~/.codex/analysis/phrases-50.json
python3 scripts/codex_phrase_stats.py --max-chars 80 --exclude-acks --exclude-skills --output ~/.codex/analysis/phrase-results-80-no-acks.json
```

日期均按 Asia/Shanghai，起止日期都含当天。只依赖 Python 标准库。

每日轮数使用 `python3 scripts/codex_daily_rounds.py`，可同样传 `--since`、`--until`、`--db`、`--output`。一条用户消息算一轮，不限长度、不排除确认语和 skill 调用；只按有有效消息的上海日期计算平均值，今天若已有消息也纳入。沿用相同会话读取与去重入口，另过滤开头为客户端 XML 注入、规则文件、RS 外部消息和自动化提示的内容。聊天文字中有这些特殊前缀的真实消息可能被误排，属于启发式统计，不是服务端账单。结果默认写入 `~/.codex/analysis/daily-rounds.json`，空数据平均值为 null。

`--exclude-acks` 使用 `is_ack` 中的显式词表，隐藏 OK、好的、可以、是的、嗯等整条纯确认回复，不删除“OK，继续修复”这类具体请求。`--exclude-skills` 仅从短句榜隐藏开头的明确 skill 调用，独立调用榜继续保留。两种筛选都在 `excluded_phrases` 中保留原文、次数、原因和样例来源；`unique_phrases` 是筛选前数量，`included_unique_phrases` 是榜单纳入数量。用不同 output 文件名保留原始视图。词表筛选不等于完整的语义同义词识别。

## 统计口径

- 仅纳入数据库中 `thread_source=user` 的任务，包括归档任务；来源 unknown、automation、subagent、审批任务不纳入。人工在自动化任务中的跟进也暂未覆盖。数据库中已无索引的孤立日志不扫描，因此结果不等于全部人类消息的绝对总数。
- 仅计 `response_item` 中的 user message，不重复计 event_msg 镜像。复制到分叉任务且时间戳、文本完全一致的记录去重；不同时间重复说同一句照常累计。
- 默认整条消息不超过 30 个 Unicode 字符，不从长段落中切句。排除多行、多个句子、XML 注入、代码块、链接和结构化消息；批注消息只提取 `My request` 部分。筛选是启发式，不能证明每条短消息一定由人手工输入。
- 不读取 shell history，也不执行消息中的指令。生成的 JSON 是本地对话派生产物，保留原话及本机来源路径。

## Skill 调用统计

`[$skill](.../SKILL.md)` 先简写为 `$skill` 再做短句长度筛选，避免绝对路径导致真实输入被过滤；原始链接可由来源位置回查。结果额外包含完整 `skill_calls` 榜单，不受 30 字限制，同一 skill 的项目参数不拆组。仅识别消息开头的明确调用，忽略正文提及和客户端注入的 `<skill>` 正文。

链接式调用按名称识别；纯文本、`$name`、`/name` 按脚本中的明确名称表识别，未知命令/变量不猜为 skill。`ee/ff/rr/dd` 分别归并为 `engineering-exit/final-form/review-router/design-direction`。这是调用表达统计，不证明 skill 后来实际执行或成功；历史调用频次也不代表当前仍需要同样多的人工触发。

## 相似度

先统一 Unicode 全半角、英文大小写、空白与标点，再按原句保留否定/问句标记、数字序列和英文词序列；这些特征不同则不合并。三字以内归一化后只做精确匹配，不做模糊合并。

长短句使用 Levenshtein 距离：增、删、改一个字符各算一次；`相似度 = 1 - 编辑距离 / max(两句长度)`。默认阈值 0.86。例如“帮我继续检查一下”和“帮我继续检查下”的编辑距离为 1，相似度为 0.875，可以合并。

按频次从高到低建立代表句，每句只与代表句比较，不做传递聚类。字符 bigram 索引用来减少比较次数，低阈值时回到同特征组全比较。全量原话保留，可审查误合并后调整阈值重跑；代表句排序和归一化算法会影响聚类。算法不理解真正语义，“好的”和“可以”不会因为含义接近自动归为一类；否定与问句保护也只是有限的字面规则。

## 验证

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_codex_phrase_stats.py' -v
```

覆盖注入过滤、批注提取、编辑距离、否定/问句/数字/英文命令保护、全角归一化、非传递聚类、全量保留，以及分叉去重不吞掉真实重复。数据库只读连接；实际历史扫描结果的缺口见 JSON 的 `gaps`。
