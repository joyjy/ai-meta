---
type: Pattern
title: UI Interaction
description: 当人类操作与 debounce、polling、后台推送或异步响应并存时，用显式交互状态、防重放和渲染提交屏障避免后台更新覆盖操作反馈。
resource:
tags: [frontend, form]
---

# UI Interaction

人类开始操作 UI 后，系统应持续让他感知“操作是否被接受、正在发生什么、结果是什么、还能做什么”。后台同步可以继续获取新数据，但不能悄悄覆盖提交反馈、提前移除 Undo、重置输入、移动当前焦点，或让较旧响应回写成新的页面状态。

这个 pattern 把一次人类操作视为有明确生命周期的 interaction transaction，并在后台 snapshot 与可见 UI 之间设置 render commit barrier。Debounce、throttle、single-flight、idempotency 和 polling 分别解决不同问题，不能互相替代。

## Context

- 页面存在提交、Resolve、删除、批量操作、搜索、分页或筛选等人类交互。
- 页面同时通过 polling、SSE、WebSocket、缓存 revalidation 或多个并发请求更新数据。
- 操作包含 loading、成功、失败、Undo、重试或乐观更新等可见反馈。
- 后台 snapshot 可能与本地 pending state 同时修改同一实体或同一片 DOM。
- MVP 实现倾向于在事件回调里直接 fetch，再用整页或整块 render 覆盖当前 UI。

如果页面只有只读内容、没有持续后台同步，或者重新加载本身就是明确且可接受的交互结果，不必引入完整协调层。

## Problem

浏览器事件循环会把用户输入、debounce timer、网络响应、poll timer、动画和 Undo 倒计时交错执行。单独看每条路径都正确，不代表组合后仍符合用户直觉：poll 可能在提交请求返回前重建 DOM；旧请求可能比新请求更晚返回；按钮虽然禁用了双击，网络重试仍可能重复写入；服务端已经成功，用户却只看到被后台 snapshot 恢复的旧状态。

常见 MVP 把 debounce 当成通用并发控制，把 `disabled` 当成防重放，把 polling 当成无条件 render 权限。它们只能限制某个入口，不能维护完整的交互生命周期，也不能证明跨请求、跨重试或跨渲染的正确性。

## Forces

- 用户需要立即、连续且可理解的反馈；后台数据也需要保持新鲜。
- Debounce 会压缩意图，适合连续输入，却可能丢掉本应执行的离散操作。
- Client-side single-flight 能阻止当前页面重复发起，但不能防止超时重试、多 tab 或代理重放。
- 服务端 snapshot 更接近事实源，但本地 pending、optimistic 和 undoable state 尚未进入该 snapshot。
- 完全暂停同步可以保护交互，却会扩大陈旧窗口；无条件同步又会破坏交互连续性。
- 整块 DOM 替换实现简单，但会丢失焦点、selection、临时反馈、倒计时和事件处理上下文。
- 网络响应没有天然顺序，先发出的请求可能最后返回。

## Pattern

先定义 interaction perception contract：

- 操作被接受后立即进入可见状态，不让用户猜按钮是否生效。
- Pending、成功、失败、可重试和 Undo 必须有稳定、连续的表现。
- 后台更新不得无提示地清除输入、焦点、错误信息、进度或尚未到期的 Undo。
- 操作失败时保留恢复路径；不能只恢复按钮而丢掉用户输入或上下文。
- 同一个业务意图无论因双击、超时重试还是传输重放再次到达，都不会重复产生副作用。

然后把人类操作建模为显式状态机，而不是几个互不相关的 boolean：

```text
idle
  → queued
  → submitting
  → succeeded
  → undoable
  → settled

submitting → failed → retrying | idle
undoable   → undoing → idle
```

后台同步使用独立生命周期：

```text
scheduled
  → fetching
  → freshness / generation check
  → commit now | defer latest snapshot
  → reconcile
  → render
```

两条生命周期通过 render commit barrier 协调：后台 fetch 可以继续执行，但在提交 UI 前必须检查目标 conflict scope 是否有 active interaction transaction。存在冲突时只保留最新 snapshot，等待操作 settled 后再 reconcile；不存在冲突时才提交渲染。

```text
Human intent ─→ Interaction transaction ─→ Local feedback overlay
                          │                         │
                          └─→ Idempotent command ──┤
                                                    ↓
Background sync ─→ Latest snapshot ─→ Commit barrier ─→ Reconcile ─→ Render
```

优先按稳定 entity key 隔离冲突，例如 `task_id`、`dedupe_key` 或 resource version。一个实体正在 Resolve 时，其他实体仍可刷新。只有现有页面只能整块重渲染时，才把整个区域作为 conflict scope。

各工具职责保持分离：

- `debounce`：把连续输入压缩为一次意图，适合搜索、校验和草稿保存；不作为提交防重放机制。
- `throttle`：限制滚动、resize、drag 或高频 refresh 的执行频率；不保证最终业务写入只发生一次。
- `single-flight` / pending guard：阻止当前 client 对同一意图并发执行，并提供即时 loading 反馈。
- `idempotency key` / 条件写入：让服务端识别同一业务意图的重放；retry 必须复用原 key，不能每次生成新 key。
- `generation`、resource version 或 `AbortController`：阻止较旧响应覆盖较新请求结果；取消请求只是优化，提交前仍要校验代际。
- `polling` / push：获取新事实，不自动获得覆盖本地 interaction state 的权限。
- local feedback overlay：保存 pending、optimistic、error 和 undo deadline；snapshot reconcile 时显式合并，而不是被整块替换。

如果只能使用整页或整块 DOM render，至少在后台请求发出前和 DOM commit 前各检查一次 interaction state，避免检查与提交之间再次进入操作的 TOCTOU race。冲突时 defer，而不是丢弃 snapshot；interaction settled 后立即应用最新 deferred snapshot，不必等待下一个轮询周期。

Polling 还应避免制造新的感知问题：内容未变化时不重渲染；短暂失败时保留 last known good view；连续失败按产品需要展示非阻塞 freshness 状态并退避，不能周期性把完整页面替换成错误页。

## Failure Modes

- 用 debounce 包裹提交按钮，误以为已经防止重复业务写入；超时 retry 或多 tab 仍产生重复副作用。
- 按钮在 `await` 之后才进入 disabled / pending，双击在第一个请求发出前穿透。
- Polling 每次都整块替换 DOM，提前清除 Resolve 的成功反馈或 5 秒 Undo。
- 只在 poll 发起前检查 busy；fetch 返回前用户开始操作，旧 snapshot 仍然覆盖 active transaction。
- 同时发起多个搜索或分页请求，不校验 generation，较旧响应最后到达并回写页面。
- 乐观移除实体后没有 rollback 或 error state，请求失败时用户无法知道数据是否真的改变。
- 为每次 retry 生成新的 idempotency key，使服务端把同一业务意图当成多个操作。
- 为了避免 race 永久暂停后台同步，异常路径没有释放 busy state，页面从此不再更新。
- 后台错误直接覆盖 last known good view，让一次短暂网络抖动看起来像数据全部消失。
- Reconcile 只比较数组位置或展示文本，没有稳定 entity key，导致焦点、selection 或 pending state 绑定到错误实体。

## Implementation Checklist

- 列出人类可触发的离散操作、连续输入和纯导航，分别选择 debounce、throttle、single-flight 或直接执行。
- 为有副作用的操作定义稳定 business intent / idempotency key，并明确 retry 是否复用。
- 用一个状态机表达 queued、submitting、success、failed、undoable 和 settled，避免多个 boolean 产生非法组合。
- 定义 background sync 的 generation / version gate，保证旧响应不能提交为新状态。
- 明确 conflict scope；优先按 entity key 协调，不默认锁住整页。
- 在 render commit 前检查 active interaction；冲突时保存最新 deferred snapshot，并在 settled 后立即 reconcile。
- 把 pending、optimistic、error、focus 和 undo deadline 作为 local overlay 保留，不让 snapshot 隐式抹除。
- 内容未变化时不重渲染；刷新失败时保留 last known good view，并提供合适的 freshness / retry 反馈。
- 确保 finally、timeout、abort 和组件销毁路径都会释放 pending state、timer 和 listener。
- 对按钮、状态消息和错误反馈保留键盘焦点与可访问名称；重要状态变化按项目门槛使用可感知但不过度打扰的 live feedback。

## Verification

- 连续双击按钮或同时按 Enter，验证只产生一个业务操作，且 pending 反馈立即出现。
- 在 debounce 窗口内继续输入，验证只压缩连续输入，不吞掉离散提交意图。
- 让 poll 在用户点击前发出、点击后返回，验证 active transaction 和反馈不会被旧 snapshot 覆盖。
- 让提交请求与两个 poll 响应乱序返回，验证只有最新合法 generation 能提交。
- 在 Undo 窗口内到达新 snapshot，验证 Undo 保持到明确过期或用户执行，不会提前消失。
- 注入超时后使用同一 idempotency key retry，验证服务端副作用只生效一次，UI 能恢复最终结果。
- 让后台同步失败后恢复，验证 last known good view 保留、错误可感知，并在恢复后自动清除。
- 对两个不同 entity 并发操作，验证一个实体的 pending 不会阻塞无关实体更新。
- 在 pending、failed 和 undoable 状态下检查键盘焦点、移动视口和组件卸载，验证没有焦点丢失、悬空 timer 或重复 listener。

## Relationships

- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
