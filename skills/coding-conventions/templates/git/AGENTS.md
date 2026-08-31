# Git 规范

## Branch 命名

- 功能分支默认以 `feat-` 开头，例如：`feat-add-vehicle-bind`；项目入口或服务端 branch regex 有声明时以更具体的策略为准
- 修复分支以 `fix-` 开头，例如：`fix-vin-validation-npe`
- 分支名不要带 agent/client 前缀，例如 `codex/`、`claude/`、`opencode/`

## Commit Message

- 使用 Semantic Commit：`<type>(<scope>): <subject>`，常用 type 为 `feat` / `fix` / `refactor` / `test` / `chore` / `docs`。
- 示例：`feat(vehicle): add bind vehicle endpoint`、`fix(auth): resolve token expiry edge case`。
- subject 用英文，首字母小写，不加句号；scope 为模块名，可省略；body 说明 why，不是 what。

## Pull / Merge Request

- PR/MR 描述含多行 Markdown 时，先写入文件并使用平台 CLI 的 file 参数；不要把长 Markdown 直接放进 shell 双引号参数。
