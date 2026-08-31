# Python 编码约定

## Project Tools

- 先按项目已有入口运行测试、lint 和 type check；优先使用 `pyproject.toml`、`tox.ini`、`noxfile.py`、`pytest.ini`、Makefile 或 README 中的命令，不自造验证流程。
- 格式化工具以项目配置为准；已有 `ruff`、`black`、`yapf`、`isort` 或 pre-commit 时使用项目既定工具。
- 测试取舍复用 `testing` 模板；Python 模板不单独展开测试价值判断。
