# node-test-kit

`node-test-kit` 是由 `coding-conventions` 管理的 Node 测试脚手架。它保留项目对 `node:test` 和 `node:assert` 的直接使用，只共享运行编排、fresh build、常用 fixture、V8 coverage 和可配置 entrypoint 诊断。

## Presets

- `node-js`：直接运行原生 JavaScript / ESM 测试。
- `node-ts-build`：每次标准测试前先执行显式 `build`，再按 suite cwd 测试编译产物，避免读取旧 `dist`。
- Vitest 不属于当前 preset；只有项目已有真实 Vite/Vitest 消费者时才增加 adapter。

## Commands

```bash
$HOME/.ai/scripts/node-test-kit init --preset node-js
$HOME/.ai/scripts/node-test-kit run
$HOME/.ai/scripts/node-test-kit diagnose --output tmp/node-test-report.json
```

`run` 执行项目配置的标准测试；`coverage` 和 `diagnose` 都启用 Node V8 coverage，并把测试结果、各 entrypoint 的独立进程数和函数 hotpath 写入 JSON。entrypoint 数只是诊断信号，不是默认 KPI。

## Config

项目根目录只需维护 `node-test.config.mjs`：

```js
export default {
  preset: "node-js",
  suites: [{ name: "default", cwd: ".", files: ["test/*.test.mjs"] }],
  coverage: { include: ["src/**"] },
  environment: { temporaryHome: true },
  diagnostics: {
    sourceRoots: ["src"],
    entrypoints: { cli_processes: "src/cli.mjs" },
  },
};
```

多 workspace TypeScript 项目可配置一个 root `build` 和多个 suite；每个 suite 保留原来的 cwd，避免脚手架改变项目运行语义。

## Fixtures

package 导出 `withTempDirectory`、`runNodeCli` 和 `listenOnLoopback`。只有两个以上项目出现相同机械 setup 时才上浮到这里；业务 fixture、断言和预算继续留在项目内。
