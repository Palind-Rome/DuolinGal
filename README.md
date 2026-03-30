<div align="center">
<img src="./image/Logo.png" alt="DuolinGal" width="400" /> 

**DuolinGal：面向 KiriKiri Z galgame 的跨语言语音转换工作流**

让你玩 galgame 时角色语音变为英语或中文！

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/Palind-Rome/DuolinGal?style=social)](https://github.com/Palind-Rome/DuolinGal)

[English README](docs/README.en.md) · [快速开始](#快速开始) · [推荐工作流](#当前推荐工作流) · [文档导航](#文档导航) · [本地 API](#本地-api) · [仓库结构](#仓库结构)

</div>

---

# TL;DR

DuolinGal 是一套面向 KiriKiri Z galgame 的本地优先研究工具链。这套工作流可以让你玩上英语或中文配音的 galgame。

这套工作流已经在《千恋＊万花》上跑通了从资源提取、台词对齐、角色数据集导出，到 GPT-SoVITS 训练、批量推理、游戏补丁回灌的全流程。

我将这套工作流生成的《千恋＊万花》英文配音补丁已经发布在了 [GitHub Releases](https://github.com/Palind-Rome/DuolinGal/releases)。下载并放入游戏目录即可玩。

工作流里主要将如下高质量的开源工具进行了集成，如果你觉得这套工作流好用，就去给它们的原仓库点个 star 吧：

- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
  负责角色语音克隆、单角色训练、多角色推理，是整条语音生成链的核心。
- [KrkrDump](https://github.com/crskycode/KrkrDump)
  负责为 KiriKiri Z 游戏准备运行时 dump 配置，帮助提取脚本与资源线索。
- [FreeMote](https://github.com/UlyssesWu/FreeMote)
  负责反编译和重建 `.scn`、`.psb`、`.psb.m` 等 KiriKiri 常见资源。
- [KirikiriTools](https://github.com/arcusmaximus/KirikiriTools)
  负责 `unencrypted/` 覆盖验证和 `patch.xp3` 打包相关工作。
- [KrkrExtract](https://github.com/xmoezzz/KrkrExtract)
  可选使用，用于离线解包或重打包 XP3 资源。
- [FFmpeg](https://ffmpeg.org/)
  负责音频裁切、重采样、格式转换和 `wav -> ogg` 转码。它不是 GitHub 仓库型项目，但同样是这条工作流的重要基础设施。

# DuolinGal

DuolinGal 是一套面向 KiriKiri Z galgame 的本地优先研究工具链。  
它把“资源提取 -> 台词对齐 -> 角色数据集导出 -> GPT-SoVITS 训练/量产 -> 游戏补丁回灌”串成了一条可复现的工程工作流，适合做：

- 英文配音补丁
- 中文配音补丁
- 角色级 TTS 研究与批量验证

当前项目重点已经从“能不能做”推进到了“怎样稳定地做出整作英文配音补丁”，并且已经在《千恋＊万花》上跑通：

- 资源提取与脚本反编译
- 台词与语音对齐
- 角色数据集导出
- GPT-SoVITS 单角色训练
- 多角色夜间顺序量产
- 批量 `wav -> ogg` 回灌
- 游戏内 `unencrypted/` 覆盖与 `patch-build` 重建

## 语言入口

- 中文：当前页面
- English: [docs/README.en.md](docs/README.en.md)

## 项目目标

当前版本的 DuolinGal 不是一个“一键完成商业补丁”的成品软件，而是一条已经工程化的研究工作流。它解决的核心问题是：

1. 把 galgame 里的文本、语音、角色拆成可训练数据
2. 让 GPT-SoVITS 在 Windows 单卡环境下稳定训练与批量推理
3. 把生成结果重新整理成游戏可直接覆盖的语音树
4. 为最终的英文语音补丁打包做准备

## 当前能力

- 分析游戏目录，识别 KiriKiri Z 常见特征
- 初始化可复现的项目工作区
- 准备 KrkrDump 运行配置
- 调用外部工具反编译 `.scn` / `.psb`
- 构建 `lines.csv` 与脚本节点索引
- 导出角色级 TTS 训练数据集
- 生成 GPT-SoVITS 训练清单与英文预览
- 生成单角色 GPT-SoVITS 训练工作区
- 生成并执行可恢复的多角色 GPT-SoVITS 量产队列
- 批量把生成语音转成游戏覆盖用 `.ogg`
- 重建项目级 `patch-build`

## 隐私与路径约定

- 真实游戏路径、工具路径、用户名只应保存在本地配置中，例如：
  - `configs/toolchain.local.json`
- `workspace/projects/`、`.env`、`.venv/` 等内容不会提交到 Git
- 仓库文档默认只使用占位符路径，例如：
  - `<GAME_DIR>`
  - `<PROJECT_ROOT>`
  - `<GPT_SOVITS_ROOT>`

## 快速开始

### 1. 安装仓库

```powershell
pip install -e .
```

### 2. 准备本地配置

复制：

- [configs/toolchain.example.json](configs/toolchain.example.json)

为：

- `configs/toolchain.local.json`

然后只编辑本地副本。

### 3. 跑最小项目流水线

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "<GAME_DIR>"
python -m duolingal init-project "<GAME_DIR>" --project-id senren-banka
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal prepare-krkrdump "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal decompile-scripts "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal build-lines "<PROJECT_ROOT>"
python -m duolingal export-dataset "<PROJECT_ROOT>" "<VOICE_DIR>"
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>"
```

## 当前推荐工作流

如果目标是像《千恋＊万花》这样，真正做出一版可玩的英文语音补丁，当前更推荐按下面这条顺序走：

```text
analyze
  -> init-project
  -> preflight
  -> prepare-krkrdump / decompile-scripts
  -> build-lines
  -> export-dataset
  -> prepare-gptsovits
  -> prepare-gptsovits-train
  -> prepare-gptsovits-production
  -> run-gptsovits-production
  -> game-ready/unencrypted
  -> patch-build
  -> prepare-final-cleanup
  -> cleanup copy review / QA
  -> final QA / final cleanup / release packaging
```

### 单角色验证

如果你还在验证某个角色是否能训出来，优先看：

- [GPT-SoVITS Training Guide](docs/gptsovits-training.zh-CN.md)
- [GPT-SoVITS Local Runbook](docs/gptsovits-local-runbook.zh-CN.md)
- [GPT-SoVITS Batch Guide](docs/gptsovits-batch.zh-CN.md)
- [GPT-SoVITS Reinject Guide](docs/gptsovits-reinject.zh-CN.md)

### 多角色量产

如果你已经准备进入夜间多角色顺序训练与推理，优先看：

- [GPT-SoVITS Production Guide](docs/gptsovits-production.zh-CN.md)

## GPT-SoVITS 量产流程

当前仓库已经支持一条 **可恢复、可夜跑** 的多角色量产队列，流程如下：

```text
export-dataset
  -> prepare-gptsovits
  -> prepare-gptsovits-production
  -> run-gptsovits-production
  -> speaker prepare
  -> speaker GPT
  -> speaker SoVITS
  -> batch infer
  -> wav -> ogg
  -> combined override tree
  -> patch-build
  -> optional game-root sync
```

更具体地说：

- `prepare-gptsovits-production`
  负责扫描角色、生成训练工作区、写出夜跑计划和 `run-production.ps1`
- `run-gptsovits-production`
  负责顺序执行：
  `前处理 -> GPT -> SoVITS -> 切权重 -> 批量推理 -> 转 OGG -> 合并覆盖树 -> 重建 patch-build`
- 队列是可恢复的
  中断后重新执行同一个 `run-production.ps1`，已完成角色会自动跳过
- 队列会持续更新：
  - `production-state.json`
  - `production-status.txt`

## 权重与产物一定要保存

这一点很重要：**训练出来的角色权重、配置和批量生成结果，都应该长期保存。**

至少建议保留这些目录：

- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/weights/gpt/`
- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/weights/sovits/`
- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/configs/`
- `<PROJECT_ROOT>/tts-production/<PLAN_NAME>/`

原因很简单：

- 这些权重是你已经花时间、显卡和调参成本换来的成果
- 它们不只是能给英文用，也能给后续其他文本版本复用

### 如果以后想做中文版《千恋＊万花》，还要重训吗？

通常来说，**优先不需要重训，而是先直接复用现有角色权重做中文推理。**

也就是说，当前更合理的默认判断是：

1. 保留现有角色的 GPT / SoVITS 权重
2. 如果以后做中文版，先准备中文文本
3. 直接用现有角色模型跑中文推理
4. 只有在听感明显不够好时，再考虑补训或重训

这能大幅减少重复训练成本。  
当然，中文文本的最终效果仍然会受以下因素影响：

- GPT-SoVITS 对该角色的跨语言泛化能力
- 中文文本预处理与断句质量
- 专有名词和角色名的发音策略

但默认顺序应该是：**先推理验证，再决定是否重训。**

## 关于“纯语气句保留原音”的策略

当前仓库已经支持基础保护：

- 纯标点英文在批次准备阶段会被跳过
- 个别被 `/tts` 判为无效文本的句子会被记录并跳过

但更强的“纯语气/弱句保留原音”规则，当前建议放到**整轮量产结束之后**做最后收尾，而不是提前加进夜跑主线。

原因是：

- 过早做强过滤，容易误删本来已经生成得不错的英文语音
- 量产先跑完，才能保住尽可能完整的第一版成果
- 最后如果删掉某些 `.ogg`，游戏会自然回退到原始日语语音

当前更推荐的顺序是：

1. 先完成整轮训练、推理、转码、覆盖树构建
2. 运行 `prepare-final-cleanup`，生成一份安全副本
3. 再在副本上清理纯语气句、叫声、拟声句
4. 用清理后的副本重建 `patch-build`
5. 最后把清理后的副本用于正式 release 打包

对应命令是：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-final-cleanup "<PROJECT_ROOT>"
```

## 文档导航

- [Feasibility and Risk Assessment](docs/feasibility.zh-CN.md)
- [Project Plan](docs/project-plan.zh-CN.md)
- [Structure and Runtime Flow](docs/structure-and-runtime.zh-CN.md)
- [Local Validation Checklist](docs/local-validation-checklist.zh-CN.md)
- [Single-line PoC Guide](docs/single-line-poc.zh-CN.md)
- [Patch Packaging Guide](docs/patch-packaging.zh-CN.md)
- [Dataset Export Guide](docs/dataset-export.zh-CN.md)
- [GPT-SoVITS Preparation Guide](docs/gptsovits-prep.zh-CN.md)
- [GPT-SoVITS Batch Guide](docs/gptsovits-batch.zh-CN.md)
- [GPT-SoVITS Reinject Guide](docs/gptsovits-reinject.zh-CN.md)
- [GPT-SoVITS Training Guide](docs/gptsovits-training.zh-CN.md)
- [GPT-SoVITS Local Runbook](docs/gptsovits-local-runbook.zh-CN.md)
- [GPT-SoVITS Production Guide](docs/gptsovits-production.zh-CN.md)

## 本地 API

可选安装 API 依赖并启动 FastAPI：

```powershell
pip install -e .[api]
$env:PYTHONPATH='src'
uvicorn duolingal.api.app:create_app --factory --reload
```

可用接口包括：

- `GET /health`
- `POST /api/analyze`
- `POST /api/projects/init`
- `POST /api/projects/preflight`
- `POST /api/projects/build-lines`
- `POST /api/projects/export-dataset`
- `POST /api/projects/prepare-gptsovits`
- `POST /api/projects/prepare-gptsovits-batch`
- `POST /api/projects/prepare-gptsovits-train`
- `POST /api/projects/prepare-gptsovits-production`
- `POST /api/projects/run-gptsovits-production`

## 仓库结构

```text
DuolinGal/
|-- apps/
|-- configs/
|-- docs/
|-- src/duolingal/
|   |-- api/
|   |-- core/
|   |-- domain/
|   `-- services/
`-- tests/
```

## 当前边界

当前仓库已经证明：

- 角色级训练可以在 Windows 单卡环境下稳定运行
- 多角色夜间量产可以持续推进
- 生成语音可以真正回灌到游戏里体验

但它目前还没有完全自动化解决：

- 专有名词发音词典
- 最佳 epoch 自动搜索
- 全自动听感 QA
- 完全无人值守的弱句/拟声句精修

所以当前更适合把 DuolinGal 看成：

- 一条已经打通的 **工程化研究工作流**
- 一个能持续产出成果的 **本地量产入口**
- 而不是已经封装完成的最终用户“一键傻瓜软件”
