---
type: Reference
title: OKF Standard
description: doc-arch-review wrapper around the upstream Open Knowledge Format v0.1 SPEC.
resource: ./okf-spec.md
upstream: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
tags: [okf, documentation-architecture]
template: ../templates/okf-knowledge-object.md
---

# OKF Standard

本文件是 `doc-arch-review` 的 OKF review wrapper。完整 upstream 副本保留在下方路径，但只在主 skill 的 conformance trigger 命中时读取：

- `okf-spec.md`

副本来源：

- https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

## Upstream Repo Context

Upstream `okf/` 目录不只是 SPEC。将来的 agent 需要按任务自行判断是否继续读取：

- `SPEC.md`: OKF v0.1 标准本体；review conformance 时优先读本地副本 `okf-spec.md`。
- `README.md`: OKF 的动机、安装、reference agent 工作流、sample 和 visualizer 说明；
  当需要理解 repo 意图或操作示例时读取。
- `bundles/`: 已生成的 OKF 示例 bundle，如 `ga4`、`stackoverflow`、
  `crypto_bitcoin`；需要真实 OKF 样例或 viewer 输出形态时读取，避免整包塞入上下文。
- `samples/`: 生成示例 bundle 的 recipe、seed 和命令材料；需要复现生成过程时读取。
- `src/reference_agent/`: PoC producer / consumer 实现，包括 BigQuery source、web
  enrichment、bundle writer 和 viewer；只有要评估生成器行为或实现 OKF tooling 时读取。
- `tests/`: reference agent、bundle、viewer 和 web 工具测试；需要确认实现契约或边界行为时读取。
- `pyproject.toml`: Python package 和依赖入口；只有要运行 upstream tooling 时读取。

不要在本 skill 内自定义 OKF schema。正常 review 只读本 wrapper；只有 wrapper 无法回答 conformance 问题或疑似与 upstream 冲突时才展开 `okf-spec.md`，冲突时以 upstream 为准。

## Core Contract

OKF v0.1 的核心是一个 Markdown 文件目录树：

| Layer | Contract |
| --- | --- |
| Bundle | 自包含的层级知识文档集合，通常是 git repo、压缩包或大 repo 的子目录。 |
| Concept | 单个知识单元，由一个 Markdown 文件表示。 |
| Concept ID | concept 文件相对 bundle 的路径，去掉 `.md` 后缀。 |
| Metadata | YAML frontmatter，普通 parser 必须能解析。 |
| Relationships | 普通 Markdown links 表示 concept 间关系。 |
| Body | frontmatter 后的标准 Markdown 内容。 |
| Navigation / history | `index.md` 是目录 listing，`log.md` 是更新时间线；二者是 reserved filenames。 |

## Frontmatter Baseline

每个非 reserved `.md` concept 文件必须有 parseable YAML frontmatter，且必须包含非空
`type` 字段。其他字段是推荐或 producer-defined metadata。

```yaml
---
type: Playbook
title: Incident response - data freshness alert
description: Steps to triage a freshness alert on the orders pipeline.
resource: https://example.com/resource
tags: [oncall, incident]
timestamp: 2026-04-12T09:00:00Z
---
```

Review 时按 upstream conformance 处理：

- `type` 缺失或为空是 OKF conformance 问题。
- `title`、`description`、`resource`、`tags`、`timestamp` 是推荐字段，不是硬必填。
- Unknown keys 应保留；consumer 不应因为未知字段拒绝文档。
- 不要为了 review 建议新增非 OKF frontmatter 字段、formatter、fontformatter 或
  `source_of_truth` 之类的项目私有 schema。只有目标 corpus 已经稳定使用并有本地约定时，
  才能把这类字段当作既有项目扩展检查。
- Source-of-truth 边界优先用普通 Markdown 正文、标题、链接、`resource` 或 `# Citations`
  表达；不要把新增 `source_of_truth` 字段当成默认修复建议。

## Path Rules

- `index.md` 和 `log.md` 是 reserved filenames，不能作为普通 concept 文档。
- Durable topic space 可用目录组织，`index.md` 做 progressive disclosure。
- Concept ID 来自文件路径；路径稳定性优先于展示标题。
- 文件和目录命名保持大小写一致；跨平台协作时避免仅大小写不同的路径。
- 避免让生成后的 URL 或 rendered path 成为 source of truth。

## Link Rules

- 关系必须先表现为普通 Markdown link，例如 `[Service Map](./services/index.md)`。
- OKF 支持 bundle-root absolute link，例如 `/tables/customers.md`，也支持普通相对 link。
- Broken links 不是 malformed；consumer 应容忍部分生成或尚未补齐的 bundle。
- Optional display metadata 只能作为 link occurrence 的伴随信息，不能取代普通 link。
- Backlinks、graph edges、hover previews、embeds、rendered footnotes 都是派生视图。
- 目标文档不应在 frontmatter 里声明“别人该如何展示我”；展示行为属于引用发生处。

## Reference Preset Extension

当某个链接需要 preview、footnote、embed 或 cite 行为时，使用普通 Markdown link
加邻近 companion metadata。基线格式：

```markdown
<!-- okf-ref target="./tables/customers.md" mode="preview" label="Customers" -->
[Customers](./tables/customers.md)
```

`mode` 描述一次引用的展示意图，而不是目标文档的固有属性。候选值：

- `link`
- `preview`
- `footnote`
- `embed`
- `cite`

更详细的取舍由主 skill 在 preview / footnote / embed / citation trigger 命中时直接加载 `okf-reference-preset-proposal.md`。

Do not invent extra reference formatter names or frontmatter formatter fields.
If a requested display behavior is not covered by OKF core or the documented
reference preset proposal, report it as a project-specific extension decision
instead of silently adding a new formatter contract.

## Doc Root Taxonomy

- `/doc`: tool-facing 或 generated-doc input space。
- `/docs`: engineering durable docs，如架构、ADR、边界、change guidance。
- `/knowledge`: long-lived domain knowledge。

Review 时应标记这些错层：

- API endpoint inventory 藏在 `/docs`，且没有生成源或 API source of truth。
- 架构、ADR、长期决策混入 `/doc`。
- `/knowledge` 复制完整接口清单或运行手册，导致和工程事实漂移。

## Review Checklist

- 非 reserved `.md` concept 文件是否有 parseable frontmatter 和非空 `type`。
- `index.md` / `log.md` 是否按 reserved filename 语义使用。
- 普通 Markdown link 是否仍是关系基线。
- Links 是否使用 OKF 支持的 bundle-root absolute 或普通相对形式。
- Reference preset metadata 是否贴近对应 link，且没有替代 link。
- Renderer-only 语义是否只是增强，而不是 source of truth。
- 是否避免新增非 OKF 的 formatter / fontformatter / `source_of_truth` 字段；如确需项目扩展，
  是否有明确本地约定并标注为非 OKF core。
- Topic space 是否应该从单文件升级为目录身份。
- `index.md` / `log.md` 是否承担局部导航和历史，而不是混入执行计划。
- `/doc`、`/docs`、`/knowledge` 是否按职责放置内容。
