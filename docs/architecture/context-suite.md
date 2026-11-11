# Context 套件

`ai-meta / context` 在客户端生命周期中补充确定性的输入事实。它不拥有业务任务、MR 状态或保存上下文的运行台账。

## 组件与 source of truth

既存插件 `ai-meta-route-context@ai-meta` 的展示名为 **AI Meta Context**，继续使用 `plugins/route-context/` 源路径与 marketplace 记录，避免使已安装客户端出现第二份插件。`hooks/hooks.json` 是 Codex 默认发现入口；不要在 manifest 中复制 hook 定义，也不要同时注册旧配置路径。

| 阶段 | 组件 | 职责 |
| --- | --- | --- |
| UserPromptSubmit | `hooks/route-context-user-prompt.js`、`scripts/route_context_resolve.py` | 将项目路径与工具路由解析为 additionalContext；规则来自 `route-context.json` |

Claude Code 不安装本插件。`~/.claude/settings.json` 的 UserPromptSubmit hook 用 node 直接运行本 checkout 的 `hooks/route-context-user-prompt.js`，复用同一解析器。仓库内修改无需重装，新会话即可生效。

套件不会创建业务任务、联网查询 MR、发送评论或改写会话文件。

项目入口 `index.md` 声明的 `abbr` 与控制目录覆盖内置项目路径，`amt` 同样遵循该规则；插件安装缓存不是项目控制目录。没有对应项目入口时才保留内置路径作为发现 fallback，后续源码修改仍须核对 checkout role 和 source identity。

## 安装与验收

插件更新使用 plugin-creator 的 cachebuster 工具，然后通过 `codex plugin add ai-meta-route-context@ai-meta` 更新安装缓存。Claude Code 不走插件安装；验收时用 `jq` 确认 `~/.claude/settings.json` 的 UserPromptSubmit 指向本 checkout 的脚本，并用示例 payload 运行该命令。`install.sh` 继续只发布共享配置/软链，不直接复制 plugin cache 或写 hook 信任状态。配置按当前 Codex 的 hook review/trust 流程批准；旧文件路径或旧 hash 的信任不能证明新 hook 已启用。

验收必须区分源码、安装与实际执行：

1. 运行输入侧两个 Python 回归，并验证 plugin manifest。
2. 检查 installed manifest/cache 与目标版本一致，再用 `hooks/list` 回读 UserPromptSubmit 的发现及信任状态。
3. 新建隔离验证会话，发送命中路由的提示，观察实际注入的 route-context。直接把 JSON 喂给脚本只能证明 adapter，不算客户端行为验收。

无真实加载/触发证据时，报告 `runtime_reload_ready` 或具体 trust 阻塞，不能宣称已生效。安装和真实样本的运行记录放交付证据，不复制进本页。

## Change guidance

新增检查先证明确定性识别条件与误报边界；默认不增加持久状态、后台扫描或多个自动补正回路。更改输入字段或发现入口时，更新对应 adapter 回归并重新执行客户端验收。目录归属与发布关系同步 source map；普通匹配规则调整不扩展全局指令。
