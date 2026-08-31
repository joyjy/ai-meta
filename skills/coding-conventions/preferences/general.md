# 通用个人偏好

这些偏好独立于 `templates/general/AGENTS.md` 维护；`sync-conventions.sh` 只会把本文件写入 `~/Documents/projects/AGENTS.md` 的 `general` 受控块，不注入具体项目 `AGENTS.md`。

- 不要为抽取而抽取方法：只要代码没有膨胀到难以理解，且逻辑边界内聚、阅读顺序清楚，保留在原位置本身就是一种可读性；抽方法应服务于复用、隔离复杂度或表达稳定概念。Service / use case 方法允许保留一屏内的业务分支和异步链，只要阅读顺序就是业务顺序；不要为了压缩主方法，把主路径叙事里的条件分支、成功 / 失败分支、阶段推进或补偿分支切成 private helper。抽出去后如果能形成稳定领域动作、跨层细节边界、外部 IO 细节或错误翻译规则，可以抽；如果只是把当前方法的一段顺序执行代码换个名字搬出去，不抽。
- 不默认为业务值建枚举：业务约束基本一定会变化，优先用字符串、配置、协议常量或项目既有契约表达；除非项目已有稳定封闭集合语义，否则不要为了“类型安全”新增 enum。
- `/doc` 保留给项目原有或工具消费的文档输入层，例如 API 文档生成输入、`description.mdx`、附件、`api-spec/` 原始切面；不要把架构方案、ADR、访谈记录或领域知识混入这里。
- `/docs` 保留给工程 durable docs，例如 architecture、ADR、decision、design、spec、migration plan、runbook；不要把可生成 API reference 或 DDD knowledge 当作普通设计文档塞进这里。
- `/knowledge` 保留给结构化或半结构化长期领域知识，例如 DDD YAML、领域访谈、状态机、业务规则和 repo knowledge；不要维护完整 API method/path/schema inventory。
- API reference 的单接口契约事实进入 OpenAPI/API Spec；跨接口流程、接入指南和业务解释写文章；长期共享领域语义写 `knowledge/` 并由文章或 spec 引用。
