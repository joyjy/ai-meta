# 普通任务提前收尾补救

源码为 `plugins/route-context/hooks/task-continuation-stop.js`，配置模板为同目录 `task-continuation-hooks.json`。本机先把 `${CLAUDE_PLUGIN_ROOT}` 替换为维护 checkout 的插件绝对路径。再把模板合入 `~/.codex/hooks.json`。新定义独立于既有 MR 链接 hook，保留后者的禁用状态。Codex 需审核并信任新 hook。文件存在或离线测试通过均不代表客户端已加载。

Codex 桌面进程的 PATH 可能缺少 Node。安装用户 hook 时，使用已核验的 Node 绝对路径。模板中的 `node` 只是占位入口。用精简 PATH 验证安装后的实际命令。

输入路由也通过用户级 UserPromptSubmit hook 调用 `route-context-user-prompt.js`。插件的同类输入 hook 保持禁用，避免重复注入。当前启用状态从 `~/.codex/hooks.json` 和 `~/.codex/config.toml` 核对。

检查器只处理普通 Codex 回合的 final。明确第一人称行动承诺会触发一次授权/完成状态回查。提出修复同时承认未执行也会触发回查。检查器不解析通用任务清单，也不根据承诺赋予业务权限。没有行动承诺的停顿可能漏检。

完成回复、人工 gate、明确暂停/取消/只讨论、Stop 已续轮时放行。出现过 Goal adapter 或 ll hot-block 调用的会话保守排除，包括已完成 Goal 的会话，避免与原控制循环竞争。

检查只读 hook 指定的 transcript，核对 session 与当前 turn identity；未知格式、缺失身份、读取失败或超过 32 MiB 均放行。Transcript 是客户端实现细节，更新后需再次回放验收。中文和英文承诺匹配只是启发式，存在漏报和误报。续轮时必须重新核对原用户请求。禁止把提示当成新授权。

验证入口为 `node --test plugins/route-context/scripts/test_task_continuation_stop.js plugins/route-context/scripts/test_context_stop.js`。真实行为验收须在信任后观察：明确承诺后发生一次 Stop block 和实际续轮，完成/人工 gate 不续轮。安装后没有这组事件之前，状态为待客户端验收。

停用时在 Codex hook 管理中禁用这个独立定义；不删除 transcript，也不禁用其他 hooks。
