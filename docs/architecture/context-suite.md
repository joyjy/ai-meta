# Context 套件

`ai-meta / context` 在客户端生命周期中补充确定性的输入事实与输出检查。它不拥有业务任务、MR 状态或保存上下文的运行台账。

## 组件与 source of truth

既存插件 `ai-meta-route-context@ai-meta` 的展示名为 **AI Meta Context**，继续使用 `plugins/route-context/` 源路径与 marketplace 记录，避免使已安装客户端出现第二份插件。`hooks/hooks.json` 是 Codex 默认发现入口；不要在 manifest 中复制 hook 定义，也不要同时注册旧配置路径。

| 阶段 | 组件 | 职责 |
| --- | --- | --- |
| UserPromptSubmit | `hooks/route-context-user-prompt.js`、`scripts/route_context_resolve.py` | 将项目路径与工具路由解析为 additionalContext；规则来自 `route-context.json` |
| Stop | `hooks/context-stop.js` | 读取 Codex Stop 输入，调用 MR 检查，只在首次漏链时要求补正 |
| 输出检查 | `scripts/mr-links.js` | 提取已观察的 MR URL、匹配唯一引用、排除已链接内容和代码 |

输入路由与输出检查共享插件包装和安装过程，不互相调用；MR 检查不进入 GTD helper，也不扩成通用指令检查器。套件不会创建业务任务、联网查询 MR、发送评论或改写会话文件。

## MR 链接检查契约

Stop 仅在 Codex 提供 `turn_id`、`transcript_path` 和 `last_assistant_message` 时工作。它从给定 transcript 最后最多 2 MiB 中读取可完整解析的 Codex `response_item`，只接受 user message 及 function/custom tool output 中的文本，不把 assistant 自己生成的链接当作来源。首次读取不扫描其他会话、数据库或项目文件，不持久化会话副本。

URL 必须是已出现的 HTTP(S) `/<group>/<repo>/-/merge_requests/<iid>`，不带账号密码、query 或 fragment。完整仓库名、basename、basename 的连字符后缀或裸 `!iid` 只有在对应唯一 URL 时才可提示；跨仓库/host 同号造成歧义时跳过。普通数字、未知引用、已存在的 Markdown 链接和代码片段不触发。单次输出最多提示 12 个引用；超过 128 KiB 的回复跳过检查。

首次发现遗漏时返回 `decision: block` 与精确 Markdown 链接，要求仅修正回复格式，不执行工具或业务动作。`stop_hook_active=true` 时不再请求续轮；若仍漏链，仅显示 warning。已有其他 Stop hook 触发续轮时，这个检查同样不追加第二轮。文件不可读、格式不支持或尾部证据不足时放行，不能因为找不到来源而编造链接。

这是 best effort：Stop 的 block 会生成补正续轮，不撤回已经展示的回复，也不直接替换最终文本。有限尾部窗口可能漏掉较早来源；transcript 格式并非稳定的公开协议，因此解析器必须保持小而显式，并以真实客户端样本验证。当前只承诺 Codex 路径，不将共享 UserPromptSubmit 包装误认为其他客户端的 Stop 已验收。

## 安装与验收

插件更新使用 plugin-creator 的 cachebuster 工具，然后通过 `codex plugin add ai-meta-route-context@ai-meta` 更新安装缓存。`install.sh` 继续只发布共享配置/软链，不直接复制 plugin cache 或写 hook 信任状态。配置按当前 Codex 的 hook review/trust 流程批准；旧文件路径或旧 hash 的信任不能证明新 hook 已启用。

验收必须区分源码、安装与实际执行：

1. 运行输入侧两个 Python 回归和 `node --test plugins/route-context/scripts/test_context_stop.js`，并验证 plugin manifest。
2. 检查 installed manifest/cache 与目标版本一致，再用 `hooks/list` 回读 UserPromptSubmit / Stop 的发现及信任状态。
3. 新建隔离 Codex 验证会话，提供有链接的 MR 来源，故意产生一次裸引用；观察真实 Stop 触发、单次续轮和补链结果。直接把 JSON 喂给脚本只能证明 adapter，不算客户端行为验收。

无真实加载/触发证据时，报告 `runtime_reload_ready` 或具体 trust 阻塞，不能宣称已生效。安装和真实样本的运行记录放交付证据，不复制进本页。

## Change guidance

新增检查先证明确定性识别条件与误报边界；默认不增加持久状态、后台扫描或多个自动补正回路。更改输入字段、transcript 解析或发现入口时，更新对应 adapter 回归并重新执行客户端验收。目录归属与发布关系同步 source map；普通匹配规则调整不扩展全局指令。
