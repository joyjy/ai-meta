# Java / Gradle 编码约定

## Verify

- 执行 Gradle 命令前先解析本机工具：优先 `./gradlew`，其次 PATH 中的 `gradle`，最后才用 `$HOME/.asdf/shims/gradle`；`asdf` 只是个人环境 fallback，不是团队项目硬依赖。
- 仅在本机可用 `asdf` 且 `asdf where java` 成功时设置 `JAVA_HOME`；不要让团队项目依赖用户必须安装 asdf。
- Li Xiang 项目必须通过 `./gradlew` 使用 wrapper 自带 Gradle 7.4 / 7.5.1；SonarLint 插件与 Gradle 8.x 不兼容，会触发 `tried to access private field AbstractCodeQualityPlugin.extension`。
- 每次修改 Java 文件后，先跑 `$GRADLE compileJava compileTestJava`，确认无编译错误再继续。
- slice 完成时运行项目已有 Gradle gate；若项目已有覆盖率或静态分析任务，一并执行，不额外发明覆盖率门槛。
- format 由 Spotless / pre-commit hook 处理；除非项目要求，agent 不需要手动跑格式化命令。

## Project Shape

- Gradle 项目应显式维护 `settings.gradle` / `settings.gradle.kts` 中的 `rootProject.name`，不要依赖 checkout 目录名推断项目名。
- 使用 `git worktree`、临时目录、agent handoff workspace 或带后缀的本地目录时，目录名常会偏离真实项目名；若未固定 `rootProject.name`，`project.name`、`archivesBaseName`、manifest metadata、发布坐标或任务输出可能跟着漂移。

## JavaDoc

- 新增或修改的方法，包括构造器、override、私有辅助方法和测试方法，应有简短准确的 JavaDoc，说明职责或必要约束，不仅复述名称和参数。路过的缺失或过时注释在当前 scope 内补齐；继承文档已准确表达契约时可明确使用 `{@inheritDoc}`，实现特有约束仍须补充。不要求无关方法全量补注释，不为显而易见的信息堆砌标签。

## Java 日志实现

- 使用项目已有日志门面与参数化占位符，异常作为独立 Throwable 参数传入；避免字符串拼接、提前序列化完整对象及仅记录异常 message。昂贵的诊断字段按实际日志级别延迟计算。
- WebFlux / Reactor 日志绑定实际订阅与终止信号，返回 Mono / Flux 或完成链构建不代表业务完成；同步 try/finally 不覆盖异步生命周期。终态处理区分 complete、error、cancel，并与 HTTP 响应提交和异常映射边界核对，不直接把 complete 等同于业务成功。
- 跨线程与异步消息显式传递项目已有的关联上下文，不假定线程 MDC 自动传播；使用 MDC 时遵循项目的上下文桥接与清理机制。HTTP 摘要字段与边界遵循 API 约定，业务事件和级别遵循通用日志约定。

## Spring Binding Pitfall

- `@NoArgsConstructor` + `@ConstructorProperties` 同时存在时，Spring Model 绑定 query/form param 只走无参构造器 + setter，`@ConstructorProperties` 的名字映射无效；若需 snake_case query param 绑定，去掉 `@NoArgsConstructor`，若 DTO 同时服务 query param 和 JSON body 且命名风格冲突，拆成两个 DTO。
