---
type: Pattern
title: 拥有异步资源的 graceful shutdown
description: 按任务放弃政策和框架已有生命周期选择关闭方式；仅为必须完成或恢复的已接受工作增加必要的 drain、交接和注册保护。
resource: https://gitlab.example.com/example-org/common/li-tools/-/merge_requests/262
tags: [lifecycle, async-execution]
---

# 拥有异步资源的 graceful shutdown

先明确退出时哪些工作允许放弃，哪些必须完成或恢复，再核对框架和资源已有的关闭语义。可放弃、可重建的刷新或计算任务，使用已有取消与关闭能力即可。

已经接受且必须完成的业务工作，优先复用框架 drain、消息重投或持久交接。已有能力不满足契约时，再补当前组件缺少的生命周期控制。

## Context

- 服务拥有 `Executor`、`Scheduler`、线程池、后台任务队列、消息消费者或其他异步工作资源。
- 组件会在 `ApplicationReadyEvent` 等启动 hook 中向 broker、registry 或协调服务创建 consumer identity、listener registration、lease 等外部注册资源。
- 异步工作可能在请求返回后继续执行，或者已经进入队列但尚未开始执行。
- 服务会经历 Spring context close、滚动发布、重启、扩缩容或其他进程退出流程。
- 任务中断可能造成数据丢失、重复执行、半完成副作用或资源泄漏。

这些信号触发关闭政策检查，不直接要求自建准入 gate、计数器或恢复协议。

## Problem

关闭资源可能丢弃排队任务或打断运行中任务。后果是否可接受，由任务契约决定。必须完成的业务工作需要收尾或可靠交接；允许放弃的工作不需要为退出新增持久恢复设施。无限等待仍可能超过平台的 termination deadline。

采用 drain 时，等待范围应包含已经接受但尚未开始的工作。框架已有可靠的等待或交接能力时，直接复用。

## Forces

- 关闭政策明确允许放弃、等待完成或可靠交接的工作。
- 自管 drain 时，准入与计数需要一致的并发边界，释放覆盖实际终止路径。
- 等待受平台 termination deadline 约束，超时后按契约取消、交接或强制关闭。
- 非预期放弃业务工作时保留可定位证据；预期取消不一律记为 `ERROR`。
- 流量摘除、消息停止消费等外围动作可能由网关或消费者负责，不能假设组件内部自动完成。
- 外部注册承载待处理工作或恢复入口时，注销须保护 pending / in-flight 和当前 ownership。
- 即使实现了 `@PreDestroy`、`Disposable` 等 hook，也只能证明 planned graceful shutdown 路径，不能承担 crash、OOM 或 `SIGKILL` 的恢复正确性。
- 周期 reaper 会引入误删活跃注册和竞态风险，只有真实运行证据证明 stale 注册持续积累时才考虑。

## Pattern

```text
允许放弃的工作 → 取消并关闭资源
必须完成或交接的工作 → 停止准入 → 有界 drain 或可靠交接 → 关闭资源
承载恢复状态的外部注册 → 核对 pending / in-flight 与 ownership → 按契约注销或保留
```

先检查框架关闭、队列确认和重投语义是否已满足当前政策。自管 drain 时，再确认“已接受”边界与计数：提交前登记，终止时释放；提交同步失败也要撤销登记。计数覆盖实际 complete、error、cancel 路径。

当前组件只承诺自己或框架能够观察、等待与交接的工作范围。任务内部另起的工作不会自动进入 drain 范围。

承载待处理工作或恢复入口的外部注册，只有在停止准入、无 pending / in-flight 且 ownership 可确认时才注销。仍有未完成工作或 ownership 不确定时，保留必要状态。临时注册的创建与释放可直接沿用框架契约。

业务承诺 crash、OOM 或 `SIGKILL` 后恢复时，恢复不能依赖进程内 hook。先复用 broker 重投、持久任务或已有 lease 能力。只有 stale 状态持续积累且能安全识别时，才考虑周期 reaper。

## Failure Modes

- 必须完成的工作在关闭时被放弃，且没有可靠交接。
- 为允许放弃的可重建任务新增持久恢复和自管 drain。
- 在 `subscribe()` 之后才增加计数，关闭线程可能在计数前观察到零并提前销毁资源。
- 只在 complete / error 时释放计数，遗漏 cancel 或提交阶段同步失败。
- drain 没有 deadline，单个卡死任务阻塞整个进程退出。
- 非预期放弃业务工作却没有可定位证据，或把预期取消一律当作错误。
- 把平台已停止流量、消费者已停止拉取当成组件内部天然保证，没有验证实际停止顺序。
- 相同任务契约的新旧资源路径使用不同关闭政策，导致一条路径丢弃必须完成的工作。
- 把任务包装进一个 `Mono` 就宣称所有异步副作用都受控；任务内部另起线程或 fire-and-forget 工作仍可能脱离 drain 边界。
- 外部注册承载待处理工作时，关闭 subscription 后无条件注销，导致工作失去恢复入口。
- 在 drain 前注销，或没有校验 ownership 就释放外部注册，让旧实例破坏后继实例的有效注册。
- 假设 `@PreDestroy` 一定执行，把 crash、OOM 或 `SIGKILL` 后的恢复依赖进程内 hook。
- 没有 stale 状态的运行证据就增加周期 reaper，误删慢任务、活跃 owner 或仍可恢复的 pending 状态。

## Implementation Checklist

- [ ] 明确哪些工作允许放弃，哪些必须完成或可靠交接。
- [ ] 先复用框架关闭、消息确认和恢复能力，只补实际缺口。
- [ ] 自管 drain 时，覆盖已接受的排队与运行中工作，核对准入、计数和释放边界。
- [ ] 有等待时核对 termination deadline，以及超时后的取消、交接或强制关闭。
- [ ] 外部注册承载恢复状态时，保护 pending / in-flight 与 ownership。
- [ ] 按业务承诺核对 crash 恢复；新增 reaper 需要实际积累证据与安全识别条件。

## Verification

只验证当前关闭政策和已采用机制，选择主路径与最大真实风险。

- [ ] 允许放弃的任务能取消并释放资源，退出不会无限等待。
- [ ] 必须完成或交接的工作在关闭后符合契约，验证已有框架的真实行为。
- [ ] 自管 gate / 计数时，验证关闭与提交并发、完成与取消、提交失败及 deadline 超时。
- [ ] 外部注册承载恢复状态时，验证注销顺序、ownership、失败保留与退出预算。
- [ ] 承诺 crash 恢复时，再用不执行 hook 的终止方式验证恢复入口。
- [ ] 采用 reaper 时，再验证它不会删除活跃 owner 或仍有待处理工作的注册。

## Relationships

- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
