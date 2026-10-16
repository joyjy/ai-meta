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

## 目标分支同步

- MR/PR 默认尽量跟上目标分支。开始创建或更新 MR/PR、准备正式回归前，获取最新目标分支，固定 source/target SHA 并检查差异。若存在尚未吸收的目标分支更新，优先按项目流程完成必要同步，再推送并运行正式回归。不要只报告落后，把同步留到用户催促。选择 merge 或 rebase 时遵守项目约定，并按下节保留两侧能力。
- 准备合并前，再核对目标分支。若目标分支变化影响本次变更或合并条件，补同步和适用验证。不因每次无关提交无限追赶或重复运行全部 CI。保留同步后的 source/target SHA 和验证证据，旧 HEAD 的绿灯不能证明新 HEAD 已通过。
- 同步沿用当前任务的执行与 Git 授权。push、强推、改写远端历史和 MR/PR 合并仍遵守各自权限边界；普通 push 授权不包含强推。缺少权限时，先完成可独立执行的本地准备，再就具体动作请求授权。目标分支或同步中的业务取舍无法确定时，不猜测。

## 合并与冲突核验

- 处理冲突或同步 stacked branch 时，固定当前分支、待合入分支的提交与 merge-base，先核对两侧各自新增的能力；squash 后历史不同不代表内容重复，不能据此整批保留一侧。
- 使用 `merge -s ours`、`-Xours/-Xtheirs` 或整文件选边前，核对将被舍弃的另一侧改动；既检查仅上游修改的文件，也检查两侧都修改的文件。已证明等价或属于明确授权的替换时可选边，不因存在差异就一律阻塞。
- 合并结果须同时对照两侧：检查相对待合入分支的删除、重命名及接口／数据契约变化，并确认当前分支有意新增的能力仍保留。同一文件可同时承载上游修复和本分支新功能，不能以整文件接受另一侧代替语义合并。
- 无冲突、当前分支树未变或 CI 通过，均不能单独证明上游能力已吸收。按真实风险核验相关消费者与回归；范围内可查的遗漏直接修复，只有无法查明的业务取舍才交还用户。完成时说明两侧重要改动的保留、等价替代或有意移除依据，不扩展为全仓审计。
