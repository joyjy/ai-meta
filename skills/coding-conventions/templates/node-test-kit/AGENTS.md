# Node Test Kit

- Node-only CLI / server 项目默认直接使用 `node:test`；不要只为统一工具而迁移 Vitest，也不要用共享脚手架包装 `test`、`assert` 或 mock API。
- 已接入 coding-conventions `node-test-kit` 时，项目只维护 `node-test.config.mjs`、标准 npm scripts、业务 fixture 和项目级预算；通用 runner、临时目录/CLI/loopback fixture、V8 coverage 与 entrypoint 诊断回到共享包维护。
- JavaScript 项目使用 `node-js` preset；测试 `tsc` 编译产物的 TypeScript 项目使用 `node-ts-build`，标准 `npm test` 必须包含 fresh build，不能把既存 `dist` 当成当前源码的测试证据。
- entrypoint 进程数和函数 hotpath 是按需诊断信号，不是默认 KPI；只有对应耗时、flaky、副作用或错误分层时才设回归门槛。
