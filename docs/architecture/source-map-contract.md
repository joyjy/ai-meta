---
type: Reference
title: Project source map contract
description: 每个受管项目的源码归属、事实源、生成关系和验证入口契约。
resource:
tags: [ai-meta, architecture, source-map, documentation]
---

# Project Source Map Contract

## Scope

每个受管源码项目都必须维护一份独立的 `docs/architecture/source-map.md`。它是面向维护者和 agent 的稳定 ownership map，不是逐文件 inventory、当前计划或实现历史。

`docs/architecture/index.md` 必须链接 source map；`AGENTS.md` 只保留一条靠前的事实源指针，不复制 source map 正文。没有 `AGENTS.md` 的项目仍必须从架构入口链接 source map。

## Required Content

source map 至少覆盖：

- 主要 source roots 的目录树，以及每个 root 拥有的职责。
- 共享协议、schema、配置或其他跨 root contract 的事实源。
- 每个主要 root 对应的架构文档和主要验证入口。
- generated artifacts、editable source 和 generator 的映射。
- `/doc`、`/docs`、`/knowledge` 等项目实际使用的文档事实层。
- 改变 ownership、协议、生成关系或验证边界时必须同步的层。

只记录稳定目录或入口，不枚举普通源码文件。项目没有某一类内容时省略该类，不为填模板制造空层。

## Presentation

source map 默认以 fenced `text` 目录树作为第一主视图，让读者先看清层级、相邻关系和主要职责：

```text
project/
├── src/                 # 产品源码
│   ├── core/            # 稳定内核
│   └── integrations/    # 外部适配
├── test/                # 公共边界验证
└── docs/architecture/   # 当前架构事实
```

- 树只展开到能够区分 ownership 的稳定层级，每行使用一个短注释说明 owner，不塞入完整句子。
- 只有会被误改的依赖方向、禁止事项或重叠边界才在树后增加 `Boundary Notes`；不要把树中每个目录再逐项复述一遍。
- 架构链接、验证命令、共享 contract 和 generated mapping 分别放在短列表中，避免把多种维度压进横向 ASCII 表。
- 表格只在确实需要逐列比较同一批对象时使用；目录归属和源码层级默认不用表格。
- 目录树是人工维护的语义地图，不得用自动生成的全量 `tree` 输出替代。

## Accuracy

一份 source map 只有同时满足以下条件才算准确：

- manifest、workspace、service 或 build metadata 声明的主要 source root 均已覆盖。
- 所有声明路径和验证入口当前存在；外部运行态路径明确标为运行态而非 repo source。
- 一个稳定职责只有一个 owner；重叠、适配层或共享 contract 有明确边界。
- 生成物指回 generator 或 editable source，不能被描述为手工维护事实源。
- 已删除、重命名或迁移的 root 不残留，新增 root 不处于无 owner 状态。
- source map 与架构入口、README、AGENTS、runbook 和附近 durable docs 不冲突。

日期或 `last verified` 文案不能替代这些证据。准确性以当前 repo tree、manifest、生成关系和验证入口为准。

## Review Ownership

`doc-arch-review` 拥有语义正确性：

- 对照 repo tree、manifest、workspace、build/test metadata 和架构文档检查完整性与 ownership。
- 关键 root、owner、共享 contract 或生成关系缺失且可能导致错误修改时报告 `P1`。
- 信息不完整但主要边界仍可判断时报告 `P2`。
- 不把自动生成目录清单当成语义 source map。

`agent-doc-hygiene` 拥有加载路径：

- 检查 `AGENTS.md` 是否有唯一、靠前且有效的 source-map 指针。
- 检查 AGENTS、README、context、memory 和其他高频入口是否复制 source map 正文或形成 competing map。
- 缺少发现入口或存在重复副本时报告 `Must Fix`。
- 不自行发明复杂 ownership；疑似语义失真时路由给 `doc-arch-review`。

## Change Triggers

只有下列结构性变化要求在同一次工程收尾中重新核对 source map：

- 新增、删除或重命名主要 source root、workspace、package 或 service。
- ownership、依赖方向、共享 contract 或跨 root 协议改变。
- generator、editable source 或 generated artifact 映射改变。
- 架构入口、主要 build/test/smoke 入口或文档事实层改变。

普通业务逻辑修改不要求机械触碰 source map。结构性 diff 未更新 source map 时，`engineering-exit` 必须运行 `doc-arch-review`；如果同时涉及 AGENTS 入口或重复内容，再运行 bounded `agent-doc-hygiene`。

## Relationships

- [Architecture index](./index.md)
- [Source-of-truth boundaries](./source-of-truth-boundaries.md)
- [Source map template](../../skills/doc-arch-review/templates/source-map.md)
- [doc-arch-review](../../skills/doc-arch-review/SKILL.md)
- [agent-doc-hygiene](../../skills/agent-doc-hygiene/SKILL.md)
- [engineering-exit](../../skills/engineering-exit/SKILL.md)

## Invariants

- 每个项目只有一份 canonical source map。
- source map 记录 ownership 和维护入口，不成为文件 inventory、计划、历史或恢复状态。
- AGENTS 负责发现，架构文档负责事实，review skill 负责验证，`engineering-exit` 负责变更时触发。
