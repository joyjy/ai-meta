---
type: Pattern
title: 拥有异步资源的 graceful shutdown
description: 当组件拥有异步工作资源或创建外部 consumer identity、listener registration、lease 时，用停止准入、drain、deadline 和有条件注销保证退出与恢复边界可解释。
resource: https://gitlab.example.com/example-org/common/li-tools/-/merge_requests/262
tags: [lifecycle, async-execution]
---

# 拥有异步资源的 graceful shutdown

只要一个组件拥有异步执行资源，就不能只把 `close`、`dispose` 或 `shutdown` 当成资源清理动作。它还需要回答：关闭开始后是否继续接收工作，已经接收的工作如何结束，最多等待多久，以及最终放弃时留下什么证据。

这个 pattern 用于识别和评审 graceful shutdown 场景，不要求所有实现共享同一个接口或类层次。不同资源可以有不同的停止和 drain 机制，但生命周期边界应当能被说明和验证。

## Context

- 服务拥有 `Executor`、`Scheduler`、线程池、后台任务队列、消息消费者或其他异步工作资源。
- 组件会在 `ApplicationReadyEvent` 等启动 hook 中向 broker、registry 或协调服务创建 consumer identity、listener registration、lease 等外部注册资源。
- 异步工作可能在请求返回后继续执行，或者已经进入队列但尚未开始执行。
- 服务会经历 Spring context close、滚动发布、重启、扩缩容或其他进程退出流程。
- 任务中断可能造成数据丢失、重复执行、半完成副作用或资源泄漏。

命中这些信号时，应把 graceful shutdown 作为生命周期能力检查，而不是只检查资源是否最终调用了 `close` / `dispose`。

## Problem

立即销毁 scheduler 或线程池会丢弃排队任务、打断运行中任务，或者让任务在没有可观测证据的情况下消失。无限等待又可能超过平台的 termination deadline，导致进程被平台强制杀死。

只统计“当前正在运行”的任务也不够：已经被接受、正在等待调度的任务同样属于关闭时需要解释的工作范围。

## Forces

- 关闭流程需要先停止新工作进入，再处理已经接收的工作。
- 准入判断和任务计数必须有一致的并发边界，不能在关闭和提交之间留下未计数的窗口。
- complete、error、cancel 以及提交 / 订阅阶段失败都必须有明确的释放路径。
- drain 必须受平台实际 termination deadline 约束，不能只依赖组件自己的默认值。
- 超时后必须允许强制关闭，但强制放弃的任务需要留下足够的 `ERROR` 证据。
- 流量摘除、消息停止消费等外围动作可能由网关或消费者负责，不能假设组件内部自动完成。
- 外部注册只能在已停止准入、drain 完成、没有 pending / in-flight 且 ownership 可确认时注销；否则要保留可恢复入口。
- 即使实现了 `@PreDestroy`、`Disposable` 等 hook，也只能证明 planned graceful shutdown 路径，不能承担 crash、OOM 或 `SIGKILL` 的恢复正确性。
- 周期 reaper 会引入误删活跃注册和竞态风险，只有真实运行证据证明 stale 注册持续积累时才考虑。

## Pattern

```text
关闭准入并停止新拉取
  → 在 deadline 内 drain 已接收工作
  → 检查 pending / in-flight 与 ownership
  → 满足安全前置条件时 best effort 注销外部注册
  → 正常路径关闭本地资源
超时 / 失败分支
  → 记录 ERROR，保留外部可恢复状态并强制关闭本地资源
```

实现或评审时，先确认组件的“已接收”边界，再确认每条终止路径都能结束等待。计数通常应在通过关闭 gate 后、提交异步工作前建立；已建立订阅后的终止由统一的 finally 逻辑处理；提交阶段同步失败不能依赖 finally，必须立即回滚计数。

这个 pattern 不要求把所有异步工作都抽象成相同 API，也不把任务内部另起的、没有纳入当前执行单元的工作自动视为可控。需要明确当前组件实际能观察和等待到哪一层。

外部注册资源遵守与创建对称的生命周期，但不等于 shutdown 时无条件删除。planned graceful shutdown 中，应先关闭准入和停止拉取，再 drain；只有确认没有 pending / in-flight 且当前实例仍拥有该注册时，才在剩余 deadline 内 best effort 注销。仍有未完成工作、ownership 不确定或注销失败时保留注册及 checkpoint，让后继实例能够 claim、replay 或等待 lease 到期。

crash、OOM 和 `SIGKILL` 不保证执行 hook，恢复路径必须独立于 `@PreDestroy`、`dispose` 或进程内 finally。外部系统需要保留可 claim / replay 的状态或有界 lease 语义。周期 reaper 不是默认补偿；只有监控或事故证明确有 stale 状态持续积累，并且能定义 owner-safe、pending-safe 的识别条件时才引入。

## Failure Modes

- 只调用 `scheduler.dispose()` 或 `executor.shutdownNow()`，没有先停止准入和 drain 已接收工作。
- 在 `subscribe()` 之后才增加计数，关闭线程可能在计数前观察到零并提前销毁资源。
- 只在 complete / error 时释放计数，遗漏 cancel 或提交阶段同步失败。
- drain 没有 deadline，单个卡死任务阻塞整个进程退出。
- 超时后强制销毁仍使用 `WARN` 或无任务数量的模糊日志，无法判断是否真的放弃了工作。
- 把平台已停止流量、消费者已停止拉取当成组件内部天然保证，没有验证实际停止顺序。
- 只为新路径增加 graceful 组件，旧的 pool / scheduler 路径仍然直接销毁，导致系统存在两套关闭语义。
- 把任务包装进一个 `Mono` 就宣称所有异步副作用都受控；任务内部另起线程或 fire-and-forget 工作仍可能脱离 drain 边界。
- 关闭本地 subscription 后无条件删除 consumer identity、listener registration 或 lease，导致 pending / in-flight 工作失去恢复入口。
- 在 drain 前注销，或没有校验 ownership 就释放外部注册，让旧实例破坏后继实例的有效注册。
- 假设 `@PreDestroy` 一定执行，把 crash、OOM 或 `SIGKILL` 后的恢复依赖进程内 hook。
- 没有 stale 状态的运行证据就增加周期 reaper，误删慢任务、活跃 owner 或仍可恢复的 pending 状态。

## Implementation Checklist

- [ ] 明确 shutdown 开始后何时拒绝新任务，以及这个 gate 与任务计数的并发边界。
- [ ] 统计已经接收但未完成的工作，而不只统计已经开始运行的工作。
- [ ] 覆盖 complete、error、cancel 和提交 / 订阅同步失败的释放路径，并保证释放幂等。
- [ ] 明确 drain deadline，并用部署平台的 termination 配置校验它，而不是只看代码默认值。
- [ ] 超时后执行可解释的 force close，并将潜在任务放弃记录为 `ERROR`。
- [ ] 日志至少包含阶段、未完成任务数量和等待 / 强制关闭的原因；高风险场景再补任务级标识。
- [ ] 明确外围流量摘除、停止消费和资源关闭之间的顺序与责任边界。
- [ ] 盘点组件创建的外部注册、owner 标识、pending / in-flight 查询能力、checkpoint 和 owner-safe 注销语义。
- [ ] planned shutdown 按“停止准入 / 拉取 → drain → 校验无 pending / in-flight 与 ownership → best effort 注销”执行；前置条件不满足时保留注册。
- [ ] 外部注销受剩余 deadline 约束；失败时保留可恢复状态并记录证据，不阻塞最终本地资源关闭。
- [ ] crash、OOM、`SIGKILL` 不经过 hook 时，仍能由后继实例 claim / replay 或通过有界 lease 恢复。
- [ ] 只有真实运行证据证明 stale 注册持续积累时才设计周期 reaper，并定义 owner-safe、pending-safe 的清理条件。
- [ ] 检查同一类资源的旧实现，避免新旧两套 shutdown 语义并存。

## Verification

- [ ] 关闭与提交并发发生时，关闭先拿到 gate 的任务被拒绝，已经计数的任务会被等待。
- [ ] 正常任务完成、任务报错、任务被 cancel、提交阶段失败后，计数都不会泄漏或重复释放。
- [ ] 有任务超过 drain deadline 时，进程不会无限等待，并输出包含未完成数量的 `ERROR` 日志后强制关闭。
- [ ] 验证平台 termination deadline 大于组件可能消耗的关闭预算，并给第二阶段强制关闭留出余量。
- [ ] 对实际使用的 scheduler / pool 验证 graceful dispose、queued task、running task 和强制 dispose 的真实行为，不只依赖接口名称推断。
- [ ] 如果任务依赖外部流量摘除或消息停止消费，验证真实部署顺序，而不是只做单元测试。
- [ ] planned shutdown 无 pending / in-flight 时，验证外部注销发生在 drain 之后；仍有未完成工作时，验证注册和 checkpoint 被保留且可恢复。
- [ ] 注入外部注销失败，验证进程仍在 deadline 内退出，日志能区分 drain、注销失败和本地强制关闭。
- [ ] 用不执行 hook 的强制终止验证后继实例可以 claim / replay 或等待 lease 到期，而不是依赖 `@PreDestroy` 清理。
- [ ] 若引入周期 reaper，用运行证据复现 stale 状态，并验证它不会删除活跃 owner、慢任务或带 pending / in-flight 的注册。

## Relationships

- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
