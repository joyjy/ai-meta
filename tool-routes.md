# Tool Routes

本文件是脱敏发行版的可移植入口。机器、账号、公司内网或其他本地项目专属路由只写入 `~/.ai/tool-routes.local.md`；若该文件存在，先在本文件确定 owner，再按任务关键词读取其中的单个匹配小节。

## Checkout identity

- 先读当前 ai-meta checkout 的 `.ai-meta-repo-role.json`。
- `distribution` checkout 在当前机器上拥有安装、使用和本地诊断；不要搜索另一个同名 repo。
- 只有用户或项目 route 给出 exact maintenance root 时，才切换到上游维护源。

## Plan / Draft 文档

- 从明确的 project route 或拥有 `index.md` 的项目控制目录解析 `<project-control-root>/docs/plan/`。
- 不从当前源码 repo、worktree、相邻目录或 basename 猜测目标。
- 未绑定项目且用户未指定路径时，在对话中返回草稿，不自行选择本机目录。

## MCP 能力发现与挂载诊断

- 当前任务的 callable tool inventory 只证明本任务已挂载什么。
- 依次区分 `not configured`、`configured but not registered`、`registered but not mounted`、`mounted but unauthenticated/unreachable`。
- 使用客户端原生只读状态命令或 service-specific auth/status 入口；安装和认证仍需用户明确请求。

## Git hosting

- GitHub 使用 `gh`，GitLab 使用 `glab`；先从当前 repo remote 或用户给出的完整 URL 解析 exact host/repository。
- 不把某个组织、hostname、reviewer 或 CI 模板当成跨机器默认值；这些内容属于 local overlay 或项目规则。
- 创建仓库、push、开 PR/MR、评论和 merge 都遵守当前任务的远端写入授权。

## Loopback 集成验证

- 只有源码、测试名或既有错误证明命令会 bind loopback 时，才为项目 runner 或 exact command 请求窄提权。
- 临时服务尽量在同一次受控执行中完成启动、readiness、consumer 验证和 exact cleanup。

## Gradle wrapper 本机缓存

- `./gradlew` 需要写 `~/.gradle` 且 sandbox 不允许时，优先为项目 wrapper 请求窄提权。
- 不为 shell、Java 或解释器申请宽泛持久前缀。

## ai-meta stable helpers

- skill 校验：`~/.ai/scripts/validate-skill <skill-dir>`。
- context 保存：`~/.ai/scripts/save-context --orchestrate <abbr> ...`。
- context 恢复证据：`~/.ai/scripts/save-context-recover`。
- timeline：`~/.ai/scripts/save-context-timeline`。

## Local extensions

`~/.ai/tool-routes.local.md` 可以登记本机项目 root、私有 hostname、个人 vault 和额外 helper。它是本机状态，不进入发行仓库；缺失时报告 capability gap，不搜索相似路径作为 fallback。
