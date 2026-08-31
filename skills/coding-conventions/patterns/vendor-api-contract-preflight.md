---
type: Pattern
title: 厂商 API 契约预检与适配隔离
description: 首次接入外部厂商 API 时，先用官方契约、社区风险信号和最小原始响应探针查明真实边界，再把非标准行为隔离在 vendor adapter 内。
resource:
tags: []
---

# 厂商 API 契约预检与适配隔离

外部厂商 API 的官方文档通常足以描述 happy path，却未必完整表达 HTTP status、`Content-Type`、错误 body、长度边界、环境差异和 SDK 隐式归一化。首次接入前应先完成 bounded contract preflight，并让厂商特有行为止于 adapter；社区“踩坑”用于发现探针方向，原始响应和官方材料才用于确认契约。

## Context

- 系统首次接入支付、身份、消息、地图、对象存储或其他外部厂商 API。
- 同一 endpoint 可能按成功或失败返回不同 media type，或在业务失败时仍返回 HTTP 2xx。
- 文档存在长度、字符集、环境、版本、配额或发布状态等隐含约束。
- 社区 SDK、博客或 issue 中出现自定义解析、魔数判断、重试补丁或特殊 header 处理。
- 厂商响应不能直接作为本系统面向客户端的稳定契约。

如果项目已经有经过生产验证、覆盖当前版本和调用方式的 adapter 与 contract test，只需核对变更域，不必为每次普通调用重复完整预检。

## Problem

只按官方示例实现 happy path，容易把“HTTP 200 即成功”“响应一定是 JSON”“SDK 已替我处理错误”等假设带入内部协议。问题往往要到非法参数、凭证失效、灰度环境、超限或真实客户端消费时才暴露，此时厂商细节已经穿透 service、controller 和前端。

相反，只照抄社区 workaround 也不可靠。诸如按 body 小于 200 字节判断错误、发现首字符是 `{` 就认定为 JSON、无条件转 Base64，都是针对样本形状的启发式，不是可验证契约；响应增长、前导空白、代理改写或截断都可能使其静默误判。

## Forces

- **文档与运行时存在时差**：官方文档是首要来源，但可能遗漏网关、SDK、环境或历史兼容行为。
- **社区信号覆盖真实失败**：issue、博客和 SDK workaround 能暴露高频坑，但可能过时、错误或只适用于特定语言栈。
- **探针应当有界**：需要覆盖真实分支，又不能为验证配额、风控或破坏性行为制造生产影响。
- **HTTP 与业务语义可能分离**：status、header、body media type 和业务错误码必须组合解释。
- **内部契约需要稳定**：上层调用方不应理解某厂商特有的响应分支、错误命名和传输细节。
- **诊断不能泄密**：原始请求和响应有证据价值，但 access token、secret、用户数据和可复用授权码不能进入日志或 fixture。

## Pattern

### 1. 建立契约清单

从官方文档和当前使用的 SDK 版本列出 method、URL、鉴权位置、request media type、成功与失败 status、`Content-Type`、body schema、字符集与长度限制、超时、配额、幂等、环境和版本差异。把“文档明确声明”和“尚待实测”分开，不用示例响应替代错误分支契约。

### 2. 做定向社区侦察

用 exact endpoint、SDK method、错误码和关键响应特征搜索官方 issue、SDK issue、博客与问答，例如组合“接口名 + 坑 / 生产 / 超限 / Buffer / JSON / timeout”。社区材料只生成风险假设和探针项；它能证明问题真实发生，不为文章中的原因判断或解决方案背书。至少回到官方材料、SDK 源码或原始 HTTP 证据确认后，才能把结论写进 adapter。

### 3. 运行最小原始响应探针

在安全测试环境对正常成功、非法参数、无效凭证和一个关键边界分别发起最小请求，记录 HTTP status、headers、raw body 类型、长度、前几个 magic bytes、错误 schema 和 request ID。不要只观察 SDK 反序列化后的对象；SDK 可能已经吞掉 status、改写异常或统一响应。

限流、扣费、消息发送、支付、删除或风控等分支不为了“覆盖完整”主动触发；优先使用官方 sandbox、已存在 evidence 或无副作用的边界 probe，并明确仍未证明的行为。

### 4. 按证据强度收敛契约

- 官方当前文档、SDK 源码和本次 raw probe 是已知契约证据。
- 多个独立社区命中说明风险具有重复性，但具体行为仍需验证版本与调用方式。
- 从某一厂商推断其他国内外厂商也会如此，只能作为 preflight 动机，不能成为实现分支。

### 5. 对混合响应逐层判别

优先使用 HTTP status 和可信的 `Content-Type` 分流。若厂商在同一 2xx endpoint 中混合返回二进制成功和 JSON 错误，且 header 缺失或不可靠，则按当前契约增加内容判别：已知成功媒体可检查完整 magic signature；JSON object 候选在去除允许的 BOM 与前后空白后，应同时满足首字符 `{`、尾字符 `}`，随后必须实际 parse 并校验预期错误字段与类型。

任何分支无法匹配已知 media signature 或错误 schema 时，返回 `unexpected_vendor_response` 并保留脱敏诊断，不把未知 body 当作成功资源。不要使用固定字节长度、单个首字符、字符串包含 `errmsg` 或 JSON parse 是否抛错作为唯一判据。

### 6. 在 adapter 终止厂商语义

把原始响应转换为本系统的稳定结果，例如 `VendorResult<BinaryAsset, VendorError>`、内部 media resource 或明确的 domain error。上层只接收结构化成功、结构化失败和未知响应，不传播厂商的混合 body、错误码命名、Base64 偏好或临时存储策略。

如果标准协议已有字段语义，厂商专有能力作为独立资源或显式扩展存在，不覆盖标准字段。资源的存储、代理、缓存和过期策略由本系统生命周期决定，不由厂商原始响应形状倒推。

## Failure Modes

- 只读官方 happy-path 示例，没有验证非法参数、凭证失效和关键边界。
- 把 HTTP 200 直接解释为业务成功，忽略 body 中的错误对象。
- 按 body 小于固定字节数判断 JSON 错误；较长错误或较短、截断的二进制会被误判。
- 只检查首字符 `{`，没有处理 BOM、空白、尾界、JSON parse 和错误 schema。
- 任何可解析 JSON 都被当成预期错误，掩盖代理错误页、网关响应或厂商契约漂移。
- 只看 SDK 返回对象，不保留 status、headers、raw media type 和 request ID 的诊断能力。
- 把图片 Buffer 无条件转成 Base64 塞进业务 JSON，放大体积并破坏缓存与流式传输。
- 让厂商字段和错误码穿透 controller、前端或标准协议，导致后续无法替换供应商或修正语义。
- 把社区帖子当作当前版本事实，或为了验证限流、扣费与写操作主动制造风险。
- 在日志、fixture 或 issue 中保存 access token、secret、用户标识或可复用授权码。

## Implementation Checklist

- 列出 method、鉴权、status、media type、schema、限制、配额、幂等、环境和版本契约。
- 搜索 exact endpoint、SDK method、错误码和异常响应特征，把社区命中转成 probe 清单。
- 确认当前 SDK 是否改写 status、headers、异常和 raw body。
- 有界验证正常成功、非法参数、无效凭证与一个关键边界，并保留脱敏 raw evidence。
- 对混合响应先使用 status 和 `Content-Type`，必要时再使用完整 media signature 与 JSON object 边界、parse、schema 校验。
- 未知响应 fail closed，输出稳定内部错误并保留 request ID，不猜测为成功。
- 用 vendor adapter 转换为内部 typed result，不让厂商 body 形状进入上层契约。
- 为二进制资源明确代理、存储、缓存、过期和清理策略，不默认 Base64。
- 对标准协议保留原字段语义，把厂商能力建模为独立资源或显式扩展。
- 对未能安全触发的配额、风控和破坏性分支标记“未证明”，不伪造完成证据。

## Verification

- Contract test 分别回放成功媒体、标准 JSON 错误、带 BOM / 空白的 JSON 错误、长错误 body、截断媒体和未知 body。
- 验证错误响应即使为 HTTP 2xx 也会进入结构化失败，而不会保存或展示为图片。
- 验证合法成功媒体不依赖固定长度，并通过当前声明的 media signature 或可信 header 识别。
- 验证可解析但不符合错误 schema 的 JSON 被归类为未知厂商响应。
- 验证 adapter 之外的 service、controller 和客户端 fixture 不包含厂商 raw body 分支。
- 验证日志和保存的 probe evidence 已移除 secret、token、个人数据和可复用授权信息。
- 在 SDK 或厂商 API 版本升级时重跑最小 probe，比较 status、headers、schema 和边界差异。

## Relationships

- [Pattern label](./label.md)
- [coding-conventions](../SKILL.md)
