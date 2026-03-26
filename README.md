# DuolinGal

DuolinGal 是一个面向 galgame 英语听力实验的本地优先工具链原型。当前仓库的目标不是立刻做成“通用英配平台”，而是先把最关键的验证链路跑通：

- 识别目标游戏目录与引擎特征
- 初始化标准化工作区
- 通过外部工具提取 XP3 资源
- 把提取出的 SCN/PSB 脚本反编译成 JSON
- 从脚本 JSON 构建 `lines.csv`
- 为后续 TTS、回注和补丁封装保留稳定的数据骨架

当前第一阶段只聚焦《千恋万花》这类 KiriKiri/KAGEX/SCN-PSB 路线作品。

## 当前状态

- 已完成最小 CLI：`analyze`、`init-project`、`list-tools`、`extract`、`decompile-scripts`、`build-lines`
- 已完成最小本地 API：健康检查、工具探测、目录分析、项目初始化、资源提取、脚本反编译、`lines.csv` 构建
- 已完成工具链配置读取、进程执行封装和日志落盘
- 已完成脚本 JSON 解析骨架与 `dataset/lines.csv`、`dataset/script_nodes.jsonl` 导出
- 已补充单元测试与 CLI 级集成测试

## 快速开始

1. 安装本项目

```powershell
pip install -e .
```

2. 准备工具链配置

- 复制 [configs/toolchain.example.json](configs/toolchain.example.json) 为 `configs/toolchain.local.json`
- 按你的本地工具路径修改
- 当前支持的模板变量：
  - `krkrextract`: `{package}`、`{output}`、`{workspace}`
  - `freemote`: `{input}`、`{output}`、`{workspace}`
- `KrkrExtract` 和 `FreeMote` 的具体命令行参数格式以你的版本为准，示例配置只演示模板替换方式

3. 运行最小闭环

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "D:\Games\SenrenBanka"
python -m duolingal init-project "D:\Games\SenrenBanka" --project-id senren-banka
python -m duolingal list-tools --config configs/toolchain.local.json
python -m duolingal extract "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka" --config configs/toolchain.local.json
python -m duolingal decompile-scripts "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka" --config configs/toolchain.local.json
python -m duolingal build-lines "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka"
```

4. 运行测试

```powershell
python -m unittest discover -s tests
```

## 本地 API

如果你想用本地 Web UI 或其他桌面壳调用，可以启用 FastAPI：

```powershell
pip install -e .[api]
$env:PYTHONPATH='src'
uvicorn duolingal.api.app:create_app --factory --reload
```

当前 API 入口包括：

- `GET /health`
- `GET /api/tools`
- `POST /api/analyze`
- `POST /api/projects/init`
- `POST /api/projects/extract`
- `POST /api/projects/decompile-scripts`
- `POST /api/projects/build-lines`

## 仓库结构

```text
DuolinGal/
|-- apps/
|   |-- api/
|   `-- web/
|-- configs/
|-- docs/
|-- src/duolingal/
|   |-- api/
|   |-- core/
|   |-- domain/
|   `-- services/
`-- tests/
```

## 重要边界

- 仓库不附带任何商业游戏资源
- 仓库当前只实现“研究型工具链骨架”，不承诺自动生成完整英配补丁
- `FreeMote`、`KrkrExtract`、`KirikiriTools` 等应作为外部依赖接入，不建议直接随仓库分发二进制

## 文档

- [可行性与风险评估](docs/feasibility.zh-CN.md)
- [修订后的项目方案](docs/project-plan.zh-CN.md)
- [项目结构与运行流程](docs/structure-and-runtime.zh-CN.md)
