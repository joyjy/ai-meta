# CLI 工程约定

## Stable Interface

- CLI 是稳定接口：参数、输出、退出码、配置路径变更按兼容性处理；不要为了内部重构随意改用户脚本会依赖的行为。

## Write Safety

- 有写操作的 CLI 必须具备 dry-run、confirm 或明确目标范围之一；`--yes` 只能跳过交互确认，不能跳过目标计算和安全检查。

## Tests

- CLI 测试优先覆盖真实命令入口和关键副作用；不为 help 文案、薄 wrapper、格式细节铺测试。
