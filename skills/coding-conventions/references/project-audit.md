# Project Audit

用于 `/cc check`、`/cc audit` 或自然语言要求检查当前 repo 的工程约定与验证能力。默认只读，只报告事实和缺口；除非用户明确要求修复，否则不创建 hook、不修改 `AGENTS.md` 或构建配置。

## Workflow

1. 检查 `AGENTS.md` / `CLAUDE.md` 是否存在并通过 import 或软链保持单一事实源；两者都不存在时明确报告缺少 agent 指令入口。
2. 检查 `coding-conventions:begin/end`：个人 / 自管项目是否具备 `general` 和有技术栈证据的模板；团队 / 外部项目是否混入 `preferences/*`、个人路径或私有 helper；marker ID 是否受支持且没有重复。
3. 检查受众分工：README 面向人说明是什么和怎么用，AGENTS 面向 agent 说明怎么写和验证，CLAUDE 通过 `@AGENTS.md` 或等价机制委托共享规则。
4. 从 `package.json`、`pyproject.toml`、`tox.ini`、`pytest.ini`、`Makefile`、`build.gradle`、`gradlew`、`pom.xml`、`Cargo.toml`、`go.mod` 等识别技术栈和验证入口。必要时检查 package scripts / dependencies 中的 React / Vue / Svelte / Next / Vite / Playwright 等前端信号，以及 `bin/`、`cli/`、`commands/` 或命令注册信号；不读取无关业务源码。
5. 检查是否有可执行的编译 / typecheck、测试、格式化、lint / 静态分析、风险匹配的覆盖率、pre-commit 或等价 gate。模板提供 hook partial 时，用 `git rev-parse --git-path hooks/<hook-name>` 定位本 clone 的 hook，比较受控 block 与当前 partial，报告缺失、重复或漂移；能精确识别的 markerless 旧模板 hook 作为迁移候选，无法归属的内容只报告、不改写。formatter hook 还要静态检查它不会把 staged 删除传给 formatter，也不会在格式化后把同一文件原本未暂存的 hunks 带入 index。
6. 检查项目文档是否给出 slice 完成时应运行的具体命令；只有原则没有命令是缺口。
7. GitLab flow、settings lint、MR baseline 或 MR 创建规则转到 `tool-routes.md`、`load-context`、`engineering-exit` 和项目 `index.md`，不复制到本 audit。

## Output

```markdown
cc 校验结果

已接入：
- <已确认的入口 / 模板 / 验证能力>

缺口：
- <缺失项>：<影响>；建议 <下一步>

建议优先级：
1. <最小修复>
2. <后续增强>
```

只把有证据的模板列为推荐；可能有用但证据不足的放入可选，不把个人偏好包装成团队缺口。
