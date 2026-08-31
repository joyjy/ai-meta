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

## Spring Binding Pitfall

- `@NoArgsConstructor` + `@ConstructorProperties` 同时存在时，Spring Model 绑定 query/form param 只走无参构造器 + setter，`@ConstructorProperties` 的名字映射无效；若需 snake_case query param 绑定，去掉 `@NoArgsConstructor`，若 DTO 同时服务 query param 和 JSON body 且命名风格冲突，拆成两个 DTO。
