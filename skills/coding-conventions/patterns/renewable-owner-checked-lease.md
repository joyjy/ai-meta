---
type: Pattern
title: 带 owner 校验与主动续期的分布式租约
description: 当分布式锁库不提供可靠自动续期时，用唯一 owner、原子续期与释放、失锁停止和必要的 fencing 保护长任务。
resource: https://gitlab.example.com/example-org/amp/example-amp-service/-/merge_requests/100
tags: [distributed-lock]
---

# 带 owner 校验与主动续期的分布式租约

分布式锁带 TTL 时，本质上是租约，不是永久互斥。如果任务可能运行超过 TTL，而所用 lib 不会自动续期，锁会在旧任务仍执行时过期，另一个实例可能重新获取锁并开始同一任务。此时系统已经失去互斥，即使旧实例最终正常完成也不能证明执行安全。

这个 pattern 使用唯一 owner token、原子续期和原子释放维护租约所有权；一旦续期失败，执行者必须把自己视为已经失锁，并在下一次副作用前停止。对于失锁后仍可能继续写入的高风险资源，还需要 fencing token 或资源侧条件写入。

## Context

- 定时任务、批处理、leader-only 工作或单例维护任务通过分布式锁避免跨实例并发。
- 锁使用固定 TTL 释放崩溃实例留下的占用。
- 单次任务耗时不稳定，可能超过初始 TTL，或进程可能发生长时间 GC、暂停、网络抖动。
- 所用 lib 不提供自动续期，或者其 watchdog、续期线程、最大持有时间和故障语义尚未确认。

如果 scheduler 已可靠保证目标 scope 内永不并发，或者任务天然允许重叠且副作用完全幂等，应先确认是否真的需要额外分布式锁。

## Problem

固定 TTL 同时承担两个冲突目标：TTL 太短会让正常长任务中途失锁，TTL 太长会让崩溃后的恢复等待过久。更危险的是，旧 owner 可能在租约过期后继续执行，或者在新 owner 获得租约后执行无条件删除，把新 owner 的锁释放掉。

仅使用 `SET NX PX` 解决了原子获取，但没有解决长任务续期、owner-safe release 和失锁后的陈旧执行者问题。

## Forces

- 任务耗时和暂停时间通常没有可靠上界。
- 进程崩溃时租约必须能自动过期，不能依赖 finally 一定执行。
- 续期和释放必须验证当前值仍属于自己，普通 `GET` 后再 `EXPIRE` / `DEL` 存在竞态。
- 网络分区或长暂停可能让旧 owner 无法及时发现自己已经失锁。
- 锁服务只能表达“当前租约 owner”，不能自动阻止旧 owner 对数据库或外部系统继续写入。

## Pattern

```text
生成唯一 owner token
  → 原子获取带 TTL 的租约
  → 在有界执行单元之间原子续期
  → 续期失败立即标记 lost ownership
  → 停止后续副作用
  → 仅 owner 可以原子释放
```

开始实现前先确认 lib 的真实语义：

- 是否自动续期，以及续期依赖独立线程、调用线程还是远端 watchdog。
- 进程暂停、网络超时和锁服务故障时，续期失败如何暴露。
- 是否限制最大持有时间，释放时是否校验 owner。
- Lock object 是否可跨线程使用，重入和异常退出语义是什么。

如果 lib 已完整提供经过验证的 owner-safe lease，应直接使用其能力，不再叠加第二套续期协议。

自建最小租约协议时：

- 获取：使用唯一、不可复用的 owner token，通过原子 `SET key owner NX PX ttl` 获取租约。
- 续期：使用 compare-and-extend 原子操作，只有 value 仍等于 owner 时才能延长 TTL。
- 检查点：把长任务拆成有界执行单元，在每个单元开始前或按独立心跳检查续期结果，避免一次调用长时间超过 TTL。
- 失锁：续期返回失败、超时或无法确认时，默认视为已经失去所有权；不继续发起新的副作用。
- 释放：使用 compare-and-delete 原子操作，只有当前 owner 能删除锁。
- 观测：记录 acquire、renew、lease-lost、release、skip 和运行时长，能够区分“锁被占用”与“执行中途失锁”。

TTL 和续期间隔不要依赖一个固定经验数字。它们需要覆盖单个不可中断执行单元、预期调度抖动和运行时暂停，同时保留足够的失锁检测窗口。任务无法拆成小于 TTL 的执行单元时，应提高 TTL、使用可靠 watchdog，或重新设计执行边界。

## Fencing Boundary

Owner token 能防止旧实例误续期或误释放新实例的锁，但不能阻止旧实例在长暂停后恢复并继续操作业务资源。只要旧 owner 在失锁后仍可能写入，单纯的分布式锁就不足以证明互斥。

高风险操作应使用单调递增 fencing token，并让目标资源拒绝小于当前 token 的写入；如果目标系统无法校验 fencing token，至少要在每个副作用前重新确认租约、使用业务幂等键或条件更新，并把残余 split-brain 风险写清楚。

## Failure Modes

- 设置固定 TTL 但不续期，任务运行时间超过 TTL 后与下一次调度或其他实例重叠。
- 续期只在整个长阶段结束后执行，阶段中途已经失锁却继续产生副作用。
- 使用 `GET` 后再 `PEXPIRE` 或 `DEL`，检查与修改之间被新 owner 抢占。
- 使用无 owner 的常量锁值，无法判断释放者和续期者是否仍是当前持有者。
- 续期失败只记录日志但继续执行，把“锁服务异常”误当成“仍然持锁”。
- 旧 owner 在新 owner 获取租约后执行无条件释放，删除新 owner 的锁。
- 把 owner token 当成 fencing token；它能证明身份，但没有单调顺序，业务资源无法据此拒绝陈旧写入。
- 未确认 lib 已有 watchdog，又额外实现一套续期，导致 TTL 和释放语义互相冲突。

## Implementation Checklist

- 确认 scheduler 自带的单实例、分片和 failover 保证，避免重复建设互斥层。
- 阅读并验证锁 lib 的获取、自动续期、失锁通知、最大持有时间和 owner-safe release 语义。
- 每次获取生成新的 owner token，不跨执行复用。
- 续期和释放都使用原子 owner compare 操作。
- 明确续期失败后的停止位置，保证下一次副作用前会检查 lost ownership。
- 将任务拆成可续期、可停止、可重放的有界执行单元。
- 对不可逆或跨系统写入评估 fencing、条件写入、幂等键或补偿策略。
- 监控任务耗时、TTL 剩余量、续期延迟、续期失败和锁竞争。

## Verification

- 让任务运行时间超过初始 TTL，验证续期期间不会出现第二个 owner。
- 暂停旧 owner 直到租约过期并让新 owner 获取，恢复旧 owner 后验证它不能续期、不能释放新锁，并会停止后续副作用。
- 注入锁服务超时或续期失败，验证执行 fail closed，而不是继续运行。
- 在 acquire 成功后终止进程，验证租约到期后其他实例能够恢复。
- 并发执行 compare-and-release，验证非 owner 无法删除当前锁。
- 如果使用 fencing token，让旧 owner 在失锁后尝试写入，验证目标资源拒绝陈旧 token。
- 如果依赖 lib 自动续期，实际运行超过初始 TTL 的任务，验证 watchdog 行为与文档一致。

## Relationships

- [基于主键扫描的破坏性清理](./primary-key-sweep-for-destructive-cleanup.md)
- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
