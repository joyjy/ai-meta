# IDaaS lintest MR Walkthrough

本规则适用于 `~/Documents/projects/iam-idaas-*` 中影响运行行为、接口、配置或业务流程的变更；纯文档变更不触发版本回归。

按以下顺序完成 walkthrough：

1. 确认项目实际使用的 `li-int-test` package、image 和 CI 入口；本次触及的链路逐步升级到 `0.8.2+`，并运行 `lintest doctor` 与测试收集命令证明新入口可用。不要要求一个 MR 一次迁完整个项目群，但不要在本次新增或继续复制旧版本入口。
2. 把 MR 改变的业务流程写成 BDD `Feature` 下的 `Scenario` / `Scenario Outline`，本地测试至少覆盖一条主路径 smoke，并用稳定的业务结果作为 golden。Python 只承载 step、fixture、adapter 或底层实现；只有 Python 用例而没有 BDD scenario 不算完成升级。既有 scenario 只有在其步骤和断言确实覆盖本次变化时才能复用。
3. 在同一 feature 或业务切面盘点既有用例，删除、合并、重构或优化至少一个低价值旧用例。确实没有合适候选时允许例外，但必须给出检查过的范围和不制造无关 churn 的理由。
4. 若业务路径包含两个 IDaaS 服务之间的真实调用，在 `iam-idaas-integration` 中使用 BDD 集成验证，两个服务都以真实服务参与；只有 IDaaS 之外的第三方依赖可按项目既有约定替代或模拟。
5. 服务制品可用后，在 `iam-idaas-integration` 中升级受影响服务的版本，重新构建或部署并运行对应 BDD 回归；即使本次不新增或修改集成用例，也必须完成这一步。

结束时给出可核对证据：lintest 版本与 doctor / collect 结果、feature 和 scenario、旧用例清理或例外说明，以及 integration 服务版本差异、实际回归命令和结果。
