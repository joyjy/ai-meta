# Java 个人偏好

这些偏好独立于 `templates/java-gradle/AGENTS.md` 维护；`sync-conventions.sh` 只会把本文件写入 `~/Documents/projects/AGENTS.md` 的 `general` 受控块，不注入具体项目 `AGENTS.md`。

- Java 方法进入方法体后，第一条语句前保留一个空行。
- 逻辑复杂时，优先用 early return / guard clause 扁平化。
- `equals` 调用方：确信非 null 的一方（枚举、常量、字面量）放左边直接调用，无需 `Objects.equals` 包裹；可能为 null 的一方放右边作为参数。
- `private` 方法紧跟第一个调用它的方法之后声明，不要统一堆到类末尾；同一 `private` 方法被多处调用时，放在第一次调用处之后。
- Java 方法上应有简短的 Javadoc 注释，说明方法职责或必要约束；不要只复述方法名、参数名或返回类型。
- Java 新增或修改的代码不使用 Hutool（`cn.hutool.*`）；优先使用 JDK 标准库、Apache Commons Lang 3（`org.apache.commons.lang3.*`）、Spring 已有能力或项目已有 helper。命中既有 Hutool 调用时，在不扩大当前 scope 的前提下替换；确有兼容或迁移约束时才保留并说明原因。
- WebFlux/Reactor 业务代码中，除非方法本身是通用 reactive operator / adapter，或框架接口契约明确要求，否则不要把 `Publisher`、`Mono`、`Flux` 作为方法参数；优先传入明确的领域值或命令，由方法内部构建 reactive chain，避免模糊订阅、错误传播和生命周期所有权。
- Spring `@ConfigurationProperties` 的外部配置 key 与对应 Java 属性名保持字面一致。Java 属性使用 lower camel case，因此 Apollo / properties 中对应层级也使用相同的 camelCase（例如 `liUserApiAuth`、`clientId`），不要依赖 relaxed binding 改写成 kebab-case，也不要同时维护两种写法。这是配置可读性与可迁移性的偏好，不代表 kebab-case 在当前 Spring Boot / Apollo runtime 一定无法绑定；排障时必须用目标版本的 Binder probe 或实际 Environment 证据确认，不能把命名偏好当成启动失败原因。
