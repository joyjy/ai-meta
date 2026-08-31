# lintest 测试约定

## Scope

- `lintest` 模板只记录项目原生 lintest / lint-test 入口、运行拓扑和验收边界；通用测试价值判断仍归 `testing` 模板。
- 先读取项目自己的 `test/README.md`、`lintest.yml`、`Dockerfile.lint`、`docker-compose.yml` 或等价说明；项目说明优先于本模板。

## Runtime Boundary

- 先区分命令运行位置：测试 runner 在容器内、宿主机、CI 还是远端环境；不要把 compose DNS、宿主端口和 CI 探活入口混用。
- 若 lintest UI 或浏览器验收运行在宿主机，访问宿主暴露端口；不要在宿主机浏览器里使用 compose service DNS。
- 若 lintest pytest / runner 运行在 compose 内，优先使用 compose service DNS 和容器端口；不要依赖宿主 `localhost` 端口。
- 前后端分离项目的 agent 集成验证，若只需证明静态 UI 与后端 proxy 契约，优先静态 build + serve 或 nginx mount `dist`；只有明确要验证镜像构建或发布一致性时，才默认走 UI image / multi-stage image。

## Gate

- 发现项目有原生 lintest gate 时，先记录入口和运行位置，再决定是否执行；不要把模板、示例或复制来的配置当作真实 project-native gate。
- 修改 lintest 配置、compose、mock 服务、fixture 或测试数据时，至少运行 `lintest doctor` 和目标用例；涉及 UI 或 target 时，还要启动 UI 并请求 `/api/targets/status`。collection 只能补充证明用例可发现，不能替代 doctor、UI target 状态或目标用例；不能运行时说明缺失环境、镜像、端口或权限。
- lintest 失败先按失败层定位：环境启动、mock 数据、服务路由、认证/headers、业务断言、报告生成。不要用宽松断言掩盖环境或契约错误。
