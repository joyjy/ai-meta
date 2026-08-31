# GitLab helpers

本目录说明 ai-meta 发布到 `~/.ai/scripts/` 的 GitLab 稳定 helper。可执行文件为保持既有用户入口，仍位于父目录并使用 `gitlab-*` 名称。

## 背景

本机 `glab` 的不同版本在 MR 文本输入、pipeline ref / ID 参数、非交互输出和 API 参数顺序上有差异。Agent 不应记忆其他版本的命令，也不需要下载一份可能随升级失效的静态 schema；常用写操作和 CI 查询通过 helper 固定接口，低频命令以当前二进制的 `glab <command> --help` 为事实源。

## 路由

- MR 创建、description 更新、reviewers 和 comments：`~/.ai/scripts/gitlab-mr`。
- Pipeline、job trace 和 merged CI lint：`~/.ai/scripts/gitlab-ci`。
- Project settings lint：`~/.ai/scripts/gitlab-project-lint`。
- Snippet、Issue、GitLab API 脚本开发和 GitLab 容器 CI：按下方低频 workflow 使用本机 `glab`。
- helper 已覆盖但失败时，先按 helper 与当前 glab / GitLab 实例的兼容性问题排查；raw `glab` 只用于取证，不成为新的默认路线。

## Helpers

### `gitlab-mr`

源码：[`../gitlab-mr`](../gitlab-mr)

- `gitlab-mr create --title <title> --description-file <file> --target-branch <branch> --yes`
- `gitlab-mr update <mr> --description-file <file>`
- `gitlab-mr reviewers add <mr> --user <username> [--expected-head-sha <sha>]`
- `gitlab-mr comments list <mr> [--state unresolved] [--author <username>]`
- `gitlab-mr comments add --inline <mr> --file <path> --line <line> --message-file <file>`

它负责 file-backed MR 描述、reviewer 合并、紧凑 discussions 读取和 positioned discussion；不负责 pipeline。`reviewers add` 按 exact active username 解析用户，保留写入前 readback 到的全部既有 reviewer，可用 `--expected-head-sha` 固定 revision，并使用 JSON `reviewer_ids` 写入后再次 readback；重复调用返回 `already_present` 且不发 PUT。写前确定失败返回 `not_applied`，写请求或写后验证无法定论时返回 `ambiguous`，调用方不得盲重试。创建和更新 description 时，输入文件只包含人工正文；helper 将其规范化到唯一的 `## User Description` 保护段，更新时保留从 `## PR Type` 开始且带 Managed PR Agent 自动生成脚注的管理尾段，并在写后 readback。既有 Managed PR Agent 尾段前若出现无法归属的未保护正文，helper 会停止而不猜测。当前任务已绑定某个 MR 时，首次 push 前先读取其 `source_branch`，再显式推送 `HEAD:<source_branch>`。MR 子命令不支持的 hostname 通过 `--repo https://<host>/<repo>` 传递，API 则使用 `glab api --hostname`。

### `gitlab-ci`

源码：[`../gitlab-ci`](../gitlab-ci)

- `gitlab-ci list --ref <branch> [--status failed]`
- `gitlab-ci get <pipeline-id> [--with-job-details]`
- `gitlab-ci trace <job-id-or-name> [--pipeline-id <id>]`
- `gitlab-ci lint --merged --ref <branch> [--include-jobs]`

查询默认使用非交互 JSON 输出。需要检查映射而不执行网络请求时，在子命令前传 `--print-command`。

下载仍在运行的 pipeline 中已成功 job 的 artifact 时，先解析 exact job ID，再调用 `glab api projects/<project-id>/jobs/<job-id>/artifacts`；不要使用 `glab job artifact <ref> <job>`，它会选择最近一条整体成功 pipeline，可能静默返回旧产物。

### `gitlab-project-lint`

源码：[`../gitlab-project-lint`](../gitlab-project-lint)

只读检查项目 MR / approval / squash / push rule 设置，并按 `gitlab.flow` 规则报告结果；不负责 CI YAML lint。

- `l1` 是 strict MR baseline，不允许 warn；`l2` 是 transitional baseline，允许 warn 并静默 14 天内已记录 WARN；`l3` 不运行 settings lint。
- `gitlab.squash` 只在 `l1` / `l2` 使用，缺失时按 `default-on` 检查。没有 `index.md` 或未声明 `gitlab.flow` 时，不从其他文档或 remote namespace 推断。
- 写回项目索引使用 `--write-index`；手动检查时显式传 `--flow` 和 `--squash`。

## 低频 workflow

### API 查询与脚本开发

- 先用 2–3 个代表性请求测量耗时和返回体大小，不把 `glab api` 串成 N+1 热路径。
- 快路径只拉列表、状态和 `iid` / `id` / `updated_at` 等轻字段；discussions、diff、jobs、approvals 按需展开。优先使用 `updated_after`、`simple=true`、`per_page`、状态过滤或 GraphQL 合并查询。
- 开发态缓存使用短 TTL 或 `updated_at` 判脏，key 至少包含 host、repo、资源类型和 iid/id。诊断慢查询时报告接口、请求/分页数量、耗时和缓存命中。
- GTD JS cache 的事实源是 `Projects/gtd/scripts/lib/gitlab/broker/*.mjs`；arch-hub release Python cache 的事实源是 `release/scripts/lib/gitlab_cache.py`。两边不互相 symlink 或复制实现，修改任一侧时检查 host + endpoint + paginate/body cache key、默认 30 秒短 TTL、进程内 memo 和原错误语义。
- 当前安装版本不支持 `glab api --jq`；先获取原始 JSON，再由 `jq` 或调用方解析。

### GitLab 容器 CI

- 只适用于 remote host 为 `gitlab.example.com` 的 OCI 镜像构建或发布任务。
- 先检查 `.gitlab-ci.yml`、includes、现有 build job、同组织成功 pipeline，以及 `example-org/build` 的 `/gitlab/docker-build.yml`；优先复用共享 Buildx 模板。
- 只有没有适用模板时才自建 builder，并先验证 registry manifest。提交前运行 merged CI lint，首次接入或换路线后以真实 pipeline 成功为最终证据。

### Snippet

- 公司 GitLab 单文件 snippet 使用 `glab api --method POST snippets` 的 `file_name` + `content`；多行 Markdown 通过临时文件和 `--field content=@<file>` 传入。
- 内部分享显式传 `visibility=internal`，创建后 readback `web_url` 和 visibility。
- 当前实例不接受新版 `files[0][file_path]` / `files[0][content]` payload，未验证升级前不使用。

### Issue 正文

- 创建：`glab api --method POST projects/<project-id>/issues --raw-field title='<title>' --field description=@<description.md>`；按需追加 assignee/label 并 readback。
- 更新：`glab api --method PUT projects/<project-id>/issues/<iid> --field description=@<description.md> --silent`；stdin 正文使用 `-F description=@-`，写后 readback。
- 不使用可能进入 template/editor 的 `glab issue create -d - --yes`，也不使用在当前 GitLab 返回 HTTP 415 的 `glab api --input -` JSON 更新路径。

## 维护边界

- [`../../tool-routes.md`](../../tool-routes.md) 只负责 GitLab 意图到入口的选择；本文件是 helper 行为、保护门禁和低频 workflow 的 source of truth。
- `route-context.json` 只注入首次操作前必须出现的 helper-first、MR description 和 artifact 防错门禁，不复制本文件的完整流程。
- GTD 等领域 skill 可以保留“不绕过领域 bridge”的数据安全规则，但不复制通用 glab 参数说明。
- helper 未覆盖的低频命令才直接使用本机 glab，并先查看当前命令的 `--help`。
