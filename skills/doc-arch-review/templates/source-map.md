# <Project> Source Map

本页只记录稳定的源码归属、跨目录契约、生成关系和验证入口。

## Directory Tree

```text
<project>/
├── <source-root>/          # <拥有的稳定职责>
│   ├── <module>/           # <需要区分的 ownership>
│   └── <module>/           # <需要区分的 ownership>
├── <test-root>/            # <验证范围>
└── docs/architecture/      # 当前架构事实
```

## Boundary Notes

- `<path>/` <只写容易误改的依赖方向、禁止事项或相邻边界；没有则删除本节>。

## Shared Contracts

- `<path>`：<跨 root 协议、schema、配置或 API 的事实源>。

## Generated Artifacts

- `<generated path>` ← `<generator or editable source>`；<是否跟踪及维护边界>。

## Documentation Layers

- `doc/`：<工具输入或生成文档资源；不存在则删除本项>。
- `docs/`：<架构、ADR、spec、migration、runbook；不存在则删除本项>。
- `knowledge/`：<长期领域知识；不存在则删除本项>。

## Architecture And Validation

- `<source-root>/`：[`<architecture doc>`](<relative path>)；`<command or stable validation entry>`。

## Change Guidance

- <ownership、协议、生成关系或验证入口变化时必须同步的层>。
