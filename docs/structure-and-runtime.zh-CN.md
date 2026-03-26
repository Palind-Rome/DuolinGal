# DuolinGal 项目结构与运行流程

这份文档只回答两件事：

1. 当前仓库是怎么组织的
2. `analyze -> init-project -> extract -> build-lines` 这条链路是怎么跑起来的

它不负责论证项目值不值得做。那部分请看 [feasibility.zh-CN.md](./feasibility.zh-CN.md) 和 [project-plan.zh-CN.md](./project-plan.zh-CN.md)。

## 1. 仓库结构总览

```text
DuolinGal/
|-- apps/
|   |-- api/
|   `-- web/
|-- configs/
|   `-- toolchain.example.json
|-- docs/
|   |-- feasibility.zh-CN.md
|   |-- project-plan.zh-CN.md
|   `-- structure-and-runtime.zh-CN.md
|-- src/duolingal/
|   |-- api/
|   |   `-- app.py
|   |-- core/
|   |   |-- aligner.py
|   |   |-- analyzer.py
|   |   |-- extractor.py
|   |   |-- parser.py
|   |   |-- process_runner.py
|   |   |-- tool_config.py
|   |   |-- tooling.py
|   |   `-- workspace.py
|   |-- domain/
|   |   `-- models.py
|   |-- services/
|   |   `-- project_service.py
|   |-- __main__.py
|   `-- cli.py
`-- tests/
```

## 2. 分层职责

### `domain`

核心数据模型层，负责定义统一的数据契约：

- `GameAnalysis`
- `ProjectManifest`
- `ToolRequirement`
- `ExtractionResult`
- `RawScriptNode`
- `AlignedLine`
- `LinesBuildResult`

这一层不关心 CLI、API 或磁盘操作。

### `core`

当前最关键的业务能力都在这里：

- `analyzer.py`
  负责扫描游戏目录并判断是否命中当前支持的游戏指纹
- `workspace.py`
  负责初始化工作区并写出 `project_manifest.json`
- `tool_config.py`
  负责读取 `toolchain.local.json`
- `tooling.py`
  负责探测工具状态并输出统一的 `ToolRequirement`
- `process_runner.py`
  负责执行外部命令并记录标准化结果
- `extractor.py`
  负责根据 manifest 和工具配置提取 `voice.xp3`、`scn.xp3`
- `parser.py`
  负责遍历脚本 JSON，提取 `RawScriptNode` 并导出 `lines.csv`
- `aligner.py`
  负责把原始节点转成当前阶段可用的对齐表

### `services`

`project_service.py` 是编排层。它自己不做复杂逻辑，只把 `core` 里的能力组织成对上层友好的入口。

### `api`

`app.py` 是最小本地 API。它不是完整后端，只是为了让后续本地 Web UI 有一个稳定调用面。

### `cli`

`cli.py` 是当前最实用的入口。项目现在仍处于“验证链路”的阶段，所以 CLI 比 UI 更重要。

## 3. 最重要的代码文件

如果你准备快速读懂当前项目，建议先看这 8 个文件：

1. [models.py](../src/duolingal/domain/models.py)
2. [analyzer.py](../src/duolingal/core/analyzer.py)
3. [workspace.py](../src/duolingal/core/workspace.py)
4. [tool_config.py](../src/duolingal/core/tool_config.py)
5. [process_runner.py](../src/duolingal/core/process_runner.py)
6. [extractor.py](../src/duolingal/core/extractor.py)
7. [parser.py](../src/duolingal/core/parser.py)
8. [project_service.py](../src/duolingal/services/project_service.py)

## 4. 调用关系

```mermaid
flowchart TD
  A["CLI / API"] --> B["ProjectService"]
  B --> C["Analyzer"]
  B --> D["Workspace"]
  B --> E["Tool Config + Tooling"]
  B --> F["Extractor + Process Runner"]
  B --> G["Parser + Aligner"]
  C --> H["Domain Models"]
  D --> H
  E --> H
  F --> H
  G --> H
```

这套结构的好处是：

- 入口足够薄
- 核心逻辑集中在 `core`
- 数据结构统一
- 将来接 Web UI、任务队列、TTS 流程时不会推倒重来

## 5. 真实运行链路

### 5.1 `analyze`

命令：

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "D:\Games\SenrenBanka"
```

做的事情：

1. `cli.py` 解析命令
2. `ProjectService.analyze()` 调用 `analyze_game_directory()`
3. `analyzer.py` 扫描目录中的 `.xp3`、`.dll`、`.exe`
4. 和已知游戏指纹比对
5. 输出 `GameAnalysis`

这一层的价值是先确认“这是不是当前支持的作品”，而不是盲目解包。

### 5.2 `init-project`

命令：

```powershell
python -m duolingal init-project "D:\Games\SenrenBanka" --project-id senren-banka
```

做的事情：

1. 先再次执行 `analyze`
2. `workspace.py` 创建标准目录
3. 写出 `project_manifest.json`
4. 写出 `directory_snapshot.json`

初始化后的目录大致如下：

```text
workspace/projects/senren-banka/
|-- raw_assets/
|-- extracted_voice/
|-- extracted_script/
|-- dataset/
|-- models/
|-- generated_voice/
|-- release/
|-- logs/
|-- project_manifest.json
`-- directory_snapshot.json
```

### 5.3 `list-tools`

命令：

```powershell
python -m duolingal list-tools --config configs/toolchain.local.json
```

做的事情：

1. `tool_config.py` 读取配置文件
2. 归一化工具键名，例如 `gpt_sovits` 和 `gpt-sovits` 都会被当成同一个工具
3. `tooling.py` 输出当前已知工具的状态

当前状态分三种：

- `found`
- `missing`
- `not_checked`

其中 `GPT-SoVITS` 目前是 `planned` 工具，所以没配置时会显示成 `not_checked`，避免误导为“现在必须安装”。

### 5.4 `extract`

命令：

```powershell
python -m duolingal extract "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka" --config configs/toolchain.local.json
```

做的事情：

1. 读取 `project_manifest.json`
2. 从工具链配置里找到 `krkrextract`
3. 用参数模板渲染实际命令
4. 调用 `process_runner.py` 执行外部工具
5. 将 `voice.xp3` 输出到 `extracted_voice/`
6. 将 `scn.xp3` 输出到 `extracted_script/`
7. 把每次提取的计划与运行结果写入 `logs/extract-*.json`

当前支持的模板变量有：

- `{package}`
- `{output}`
- `{workspace}`

### 5.5 `build-lines`

命令：

```powershell
python -m duolingal build-lines "D:\DuolinGal\DuolinGal\workspace\projects\senren-banka"
```

做的事情：

1. 遍历 `extracted_script/` 下的 `*.json`
2. 递归查找看起来像对话节点的字典结构
3. 尽量提取：
   - `speaker_name`
   - `voice_file`
   - `jp_text`
   - `en_text`
4. 写出 `dataset/script_nodes.jsonl`
5. 通过 `aligner.py` 生成 `dataset/lines.csv`

当前解析器是“中间层骨架”，不是完整的 SCN/PSB 反编译器。它的目标是先证明：我们能把脚本 JSON 变成可审查的训练/合成数据表。

## 6. API 运行链路

启动：

```powershell
pip install -e .[api]
$env:PYTHONPATH='src'
uvicorn duolingal.api.app:create_app --factory --reload
```

当前 API：

- `GET /health`
- `GET /api/tools`
- `POST /api/analyze`
- `POST /api/projects/init`
- `POST /api/projects/extract`
- `POST /api/projects/build-lines`

它们本质上都是对 `ProjectService` 的一层薄包装，目的是给本地前端提供稳定接口，而不是提前堆一个很重的后端。

## 7. 当前测试覆盖

当前测试已经覆盖到这些部分：

- 目录识别
- 工作区初始化
- 工具链配置读取
- 命令执行封装
- 资源提取骨架
- 脚本 JSON 解析
- CLI 级的 `extract` 和 `build-lines`

运行命令：

```powershell
python -m unittest discover -s tests
```

## 8. 现在还缺什么

当前版本已经有“可验证闭环”，但还远不是完整产品。最关键的缺口仍然是：

- 真实的 SCN/PSB 反编译接入
- 文本与语音的高精度对齐
- FFmpeg 音频处理流水线
- GPT-SoVITS 训练与推理接入
- 补丁封包与回注验证

## 9. 一句话总结

当前仓库已经从“想法”进到“能做真实验证的工程骨架”阶段了。你现在真正该关注的，不是继续美化结构，而是尽快用《千恋万花》的真实资源把 `extract -> build-lines -> 10 条回注验证` 跑起来。
