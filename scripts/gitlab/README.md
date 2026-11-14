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
- `gitlab-mr update <mr> --description-file <file> [--title <title>]`
- `gitlab-mr update <mr> --title <title>`
- `gitlab-mr update <mr> --replace <old> <new> [--title <title>]`
- `gitlab-mr reviewers add <mr> --user <username> [--expected-head-sha <sha>]`
- `gitlab-mr comments list <mr> [--state unresolved] [--author <username>]`
- `gitlab-mr comments add --inline <mr> --file <path> --line <line> --message-file <file>`
- `gitlab-mr comments add --general <mr> --message-file <file>`：发布顶层、可解决的 discussion（如阻塞性评审），写后核对 `resolvable: true`；不要改用 Notes API，它创建的是不可解决的普通评论。
- `gitlab-mr comments reply <mr> --discussion <discussion_id> --message-file <file>`：在已有 discussion 里回复，不改变 resolved 状态；写入前先读取该 discussion，ID 不属于这个 MR 时直接失败。`--dry-run` 只核对并打印请求。
- `gitlab-mr usage`：输出本机调用统计 JSON。

`<mr>` 可以是 MR URL、分支名或 IID。只给 IID 时必须同时传 `-R/--repo`，否则 helper 在任何查询前报错；IID 只在单个项目内唯一，不从 shell 当前目录推断项目。

它负责 file-backed MR 描述、reviewer 合并、紧凑 discussions 读取和 positioned discussion；不负责 pipeline。`reviewers add` 按 exact active username 解析用户，保留写入前 readback 到的全部既有 reviewer，可用 `--expected-head-sha` 固定 revision，并使用 JSON `reviewer_ids` 写入后再次 readback；重复调用返回 `already_present` 且不发 PUT。写前确定失败返回 `not_applied`，写请求或写后验证无法定论时返回 `ambiguous`，调用方不得盲重试。使用 `--description-file` 创建和更新 description 时，输入文件只包含人工正文；helper 将其规范化到唯一的 `## User Description` 保护段，更新时保留从 `## PR Type` 开始且带 Managed PR Agent 自动生成脚注的管理尾段，并在写后 readback。既有 Managed PR Agent 尾段前若出现无法归属的未保护正文，helper 会停止而不猜测。当前任务已绑定某个 MR 时，首次 push 前先读取其 `source_branch`，再显式推送 `HEAD:<source_branch>`。MR 子命令不支持的 hostname 通过 `--repo https://<host>/<repo>` 传递，API 则使用 `glab api --hostname`。

`update --replace` 精确替换唯一出现的旧文本。它保留描述中的其他字符，不添加保护标题。旧文本为空、未出现或出现不止 1 次时，命令停止。`--replace` 与 `--description-file` 互斥。含换行或 shell 特殊字符的正文，使用程序参数数组传入，避免 shell 展开。

标题和描述通过同一次请求更新。命令只写指定字段，并逐字段回读。`--dry-run` 读取当前 MR，只输出拟写字段。写前再次检查目标字段是否变化。检查不能提供服务端原子锁，检查后仍可能发生竞争。写入或回读失败时，结果标为 ambiguous；先读远端状态，禁止盲目重试。

`GitLabMrUpdateResult@1` 是执行结果，`verified_fields` 只证明列出的字段。`unchanged` 表示无需写入。

创建 MR 时，helper 读取目标项目的 squash 和删除源分支默认值，并显式传入 glab。调用方通过额外参数指定 `--squash-before-merge=true|false` 或 `--remove-source-branch=true|false` 时，保留显式选择。与项目强制 squash 策略冲突时，在创建前拒绝。

创建后回读目标项目身份及两项 MR 选项。回读失败会报告 MR 已创建，禁止重复创建。项目 setting lint 不替代此项核验。`--dry-run` 保持离线，仅预览命令，项目默认值在实际执行时解析。

### `gitlab-ci`

源码：[`../gitlab-ci`](../gitlab-ci)

- `gitlab-ci list --ref <branch> [--status failed]`
- `gitlab-ci get <pipeline-id> [--with-job-details]`
- `gitlab-ci get --mr <iid-or-url> [-R <repo>] [--with-job-details]`
- `gitlab-ci get --sha <full-sha> -R <repo> [--with-job-details]`
- `gitlab-ci wait <pipeline-id> -R <repo> [--timeout 900] [--interval 10]`
- `gitlab-ci wait --mr <iid-or-url> [-R <repo>]`
- `gitlab-ci wait --sha <full-sha> -R <repo>`
- `gitlab-ci usage`
- `gitlab-ci trace <job-id-or-name> [--pipeline-id <id>]`
- `gitlab-ci lint --merged --ref <branch> [--include-jobs]`

查询默认使用非交互 JSON 输出。需要检查映射而不执行网络请求时，在子命令前传 `--print-command`。

流水线 ID、`--mr`、`--sha` 三选一。MR IID 和 SHA 要求显式 `-R`。MR URL 自带项目，禁止同时传 `-R`。SHA 必须完整，选择该 SHA 下 ID 最大的流水线。MR 使用 API 的 `head_pipeline`，保留流水线实际所属项目。

MR head pipeline 的 SHA 必须匹配 MR head。合并结果流水线若使用合成 SHA，改用显式 pipeline ID。选择后固定 pipeline ID，不追随新流水线。尚无流水线时，返回明确错误，不等待创建。

`wait` 是同步、有总时限的只读等待。总时限默认 900 秒，包含请求耗时和休眠。轮询默认间隔 10 秒。`manual` 立即返回，禁止当作成功。等待 MR 时会复查 MR SHA 和 head pipeline；变化时返回 `superseded`。长任务的异步接续与回传仍走 tool-routes 的 RS Pipeline 入口。

选择器和 `wait` 输出 `GitLabPipelineResult@1`，供分析使用。`selection` 绑定输入和实际对象，`pipeline` 是最近观察值。`complete` 仅表示已观察到流水线终态，不表示通过。需要通过时，同时核对 `outcome=success` 与目标 SHA。作业摘要分页读取，只包含 jobs，不包含下游 bridge pipelines。结果允许摘录，禁止改写对象身份、状态或完整性。

`get` 查询成功退出 0，不代表流水线通过。`wait` 退出码：0 表示成功，3 表示失败、取消、跳过或手工等待。4 表示 MR 已变化，124 表示超时，1 表示查询错误。参数错误退出 2。旧的直接查询保持原输出。选择器只输出 JSON，且不支持 `--print-command`。

`usage` 复用本地统计，仅记录命令名、耗时和退出码。

API 依据：[Pipelines](https://docs.gitlab.com/api/pipelines/)、[Merge requests](https://docs.gitlab.com/api/merge_requests/)。

下载仍在运行的 pipeline 中已成功 job 的 artifact 时，先解析 exact job ID，再调用 `glab api projects/<project-id>/jobs/<job-id>/artifacts`；不要使用 `glab job artifact <ref> <job>`，它会选择最近一条整体成功 pipeline，可能静默返回旧产物。

### `gitlab-project-lint`

源码：[`../gitlab-project-lint`](../gitlab-project-lint)

只读检查项目 MR / approval / squash / push rule 设置，并按 `gitlab.flow` 规则报告结果；不负责 CI YAML lint。

- `l1` 是 strict MR baseline，不允许 warn；`l2` 是 transitional baseline，允许 warn 并静默 14 天内已记录 WARN；`l3` 不运行 settings lint。
- `l2` 允许 0 人审批（无 All Members 规则也符合）；当项目 pipeline 列表确认为空时，不要求开启成功流水线门禁。已有 pipeline 或适用性未知时仍检查；查询失败不按无 CI 处理。`l1` 保持至少 1 人审批及成功流水线要求。
- `gitlab.squash` 只在 `l1` / `l2` 使用，缺失时按 `default-on` 检查。没有 `index.md` 或未声明 `gitlab.flow` 时，不从其他文档或 remote namespace 推断。
- 写回项目索引使用 `--write-index`；手动检查时显式传 `--flow` 和 `--squash`。
- `--scan-branches` 分页检查既有分支，使用本工具的目标正则 `^(epic|feat|fix|test|doc|proposal)-`。扫描不依赖远端当前正则，可用于配置 push rule 前检查存量；不接受任意 RE2 表达式。默认分支按 [GitLab push rules](https://docs.gitlab.com/user/project/repository/push_rules/) 豁免。仅适用于 `l1` / `l2`，不能与 `--resolve-only` 合用。
- 扫描 JSON 放在独立的 `branch_scan`，包含 repo、schema、complete、目标正则、默认分支、count 和 violations。settings 的 status / findings 及索引写回含义不变。发现违规分支时退出 1，查询失败或分页重复时退出 2，不输出完成结果。complete 只表示分页读完，不保证扫描期间远端没有变化。
- `gitlab-project-lint usage` 输出本地调用统计；不记录参数值。
- 修改 push rule（如 `branch_name_regex`）时先 `glab api projects/<id>/push_rule` 读取：已存在用 `PUT` 只改目标字段，不存在才 `POST`（已存在时 POST 返回 422）；写后复跑本 lint。

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

- 读取 GitLab snippet 优先使用 `glab api`；本机 `glab snippet` 没有读取子命令不表示缺少读取能力。所有读取命令显式传 `--hostname <URL中的host>`，不从 cwd 推断实例或项目；联网仍遵守本文件的权限边界。
- 从 URL 区分个人 snippet（`/snippets/<id>` 或 `/-/snippets/<id>`）与项目 snippet（`/<project-path>/-/snippets/<id>`，旧链接可能省略 `/-`）。项目路径须完整 URL 编码（包括 `/`），或使用已核实的 project ID；不能仅凭 snippet 数字 ID 猜项目。
- 个人 snippet：先用 `glab api --hostname <host> --method GET 'snippets/<id>'` 读取元数据，核对身份，再用同样参数读取 `'snippets/<id>/raw'` 的正文。
- 项目 snippet：先用 `glab api --hostname <host> --method GET 'projects/<encoded-project-path-or-id>/snippets/<snippet-id>'` 读取元数据，核对身份，再用同样参数读取该 endpoint 加 `/raw` 的正文。
- 多文件 snippet 按已核实的 ref 与文件路径，读取上述元数据 endpoint 加 `/files/<encoded-ref>/<encoded-file-path>/raw`；不要把单次 `/raw` 响应当作全部文件。ref 与文件清单从元数据或仓库信息取证，不猜 `main` / `master`。
- 只有 API 无法满足需求或用户明确要求查看页面时才使用浏览器，并说明具体缺口；认证、网络失败先按既有权限流程处理，不静默改走网页。API 参考：[个人 snippet](https://docs.gitlab.com/api/snippets/)、[项目 snippet](https://docs.gitlab.com/api/project_snippets/)。
- 公司 GitLab 单文件 snippet 使用 `glab api --method POST snippets` 的 `file_name` + `content`；多行 Markdown 通过临时文件和 `--field content=@<file>` 传入。
- 内部分享显式传 `visibility=internal`，创建后 readback `web_url` 和 visibility。
- 当前实例不接受新版 `files[0][file_path]` / `files[0][content]` payload，未验证升级前不使用。

### Issue 正文

- 创建：`glab api --method POST projects/<project-id>/issues --raw-field title='<title>' --field description=@<description.md>`；按需追加 assignee/label 并 readback。
- 更新：`glab api --method PUT projects/<project-id>/issues/<iid> --field description=@<description.md> --silent`；stdin 正文使用 `-F description=@-`，写后 readback。
- 不使用可能进入 template/editor 的 `glab issue create -d - --yes`。
- 更新 Issue 的 `assignee_ids` 数组时，使用 `glab api --method PUT projects/<project-id>/issues/<iid> -H 'Content-Type: application/json' --input <payload.json>`，JSON 正文为 `{"assignee_ids":[<user-id>]}`。写后回读 assignees。此路径已有成功写入证据；历史 HTTP 415 不足以否定带此请求头的 JSON 路径。其他字段仍按当前实例契约验证。

## 维护边界

- [`../../tool-routes.md`](../../tool-routes.md) 只负责 GitLab 意图到入口的选择；本文件是 helper 行为、保护门禁和低频 workflow 的 source of truth。
- `route-context.json` 只注入首次操作前必须出现的 helper-first、MR description 和 artifact 防错门禁，不复制本文件的完整流程。
- GTD 等领域 skill 可以保留“不绕过领域 bridge”的数据安全规则，但不复制通用 glab 参数说明。
- helper 未覆盖的低频命令才直接使用本机 glab，并先查看当前命令的 `--help`。
