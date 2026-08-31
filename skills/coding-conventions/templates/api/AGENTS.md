### API 设计约定

#### Surface First

- 新增或调整 API 前，先明确调用方、调用方式、鉴权责任方、audience、scope 和代码归属；`internal` 只表示被动接收且鉴权不由本服务负责的 callback、webhook、调度或系统编排入口，不是同步服务间私有 API 的同义词。
- 同步服务间 API 放在项目声明的 server / service surface；用户本人、外部开放平台和被动 ingress 分别进入 client、open 和 internal / external surface。包名表达传输与鉴权边界，资源名表达业务能力。

#### Resource And Contract

- Controller 按资源或资源关系划分，不按动作、流程、查询维度或调用方临时聚合；同一聚合下的不同权限边界、生命周期或数据暴露面可以拆成不同资源。
- 请求和响应使用面向该用例的 DTO，只暴露调用方完成任务所需的最少字段；不要因为字段相同复用持久化模型、领域模型或更宽的历史响应。
- scope 使用最小业务能力表达，新增高风险接口必须覆盖无 token、scope 不足和允许路径；错误响应应提供稳定的机器可读 code，只有调用方确实需要时才附加 reason / details。

#### Compatibility

- 兼容入口必须有可指认的真实调用方或明确迁移成本；保留时把旧协议视为 adapter，新旧入口调用同一个应用用例，并分别用契约测试锁定路径、字段、状态码、header 和错误语义。
- 不在缺少调用方证据时收紧旧入口 scope 或删除旧字段。长期兼容也要明确 source of truth；迁移、下线或权限收紧必须先有调用方观测与回归证据。

#### Source Of Truth And Verification

- OpenAPI / API Spec 负责 method、path、schema 和错误契约；API catalog / surface map 负责 audience、能力分组、owner 与可发现性；领域知识只维护长期业务语义，不复制完整接口清单。
- API 变更同步维护项目声明的 catalog / map，并验证真实消费者主路径；跨服务认证和权限边界不能只用绕过鉴权的 controller test 证明。
