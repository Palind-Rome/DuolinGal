<div align="center">
<img src="./image/Logo.png" alt="DuolinGal" width="400" /> 

**🪄 DuolinGal：面向 KiriKiri Z galgame 的跨语言语音转换工作流**

让你玩 galgame 时角色语音变为英语或中文！

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/Palind-Rome/DuolinGal?style=social)](https://github.com/Palind-Rome/DuolinGal)

[English README](docs/README.en.md) · [快速开始](#快速开始) · [工作流](#按目标选择路径) · [文档导航](#文档导航) · [本地 API](#本地-api) · [仓库结构](#仓库结构)

</div>

---

# 🧭 TL;DR

DuolinGal 是一套面向 KiriKiri Z galgame 的本地优先研究工具链。这套工作流可以让你玩上英语或中文配音的 galgame。

这套工作流已经在《千恋＊万花》上跑通了从资源提取、台词对齐、角色数据集导出，到 GPT-SoVITS 训练、批量推理、游戏补丁回灌的全流程。

我将这套工作流生成的《千恋＊万花》英文配音补丁已经发布在了 [GitHub Releases](https://github.com/Palind-Rome/DuolinGal/releases)。下载并放入游戏目录即可玩。

这套工作流里，主要调用了如下核心工具，它们非常优秀，为它们的仓库点个 star 吧：
- [GARbro](https://github.com/morkt/GARbro)
  负责解包。
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
  负责角色语音克隆、角色训练、角色推理，是整条语音生成链的核心。
- [FreeMote](https://github.com/UlyssesWu/FreeMote)
  负责反编译和重建 `.scn`、`.psb`、`.psb.m` 等 KiriKiri 常见资源。
- [KirikiriTools](https://github.com/arcusmaximus/KirikiriTools)
  负责 `patch2.xp3` 打包；游戏运行补丁 `version.dll`。
- [FFmpeg](https://ffmpeg.org/)
  负责音频裁切、重采样、格式转换和 `wav -> ogg` 转码。
- [KrkrDump](https://github.com/crskycode/KrkrDump)
  负责解包。
- [KrkrExtract](https://github.com/xmoezzz/KrkrExtract)
  负责解包或重打包 XP3 资源。

> 注：在我本次进行千恋万花的英文生成时，使用的解包工具为 `GARbro`。虽然代码里预留了 `KrkrDump` 和 `KrkrExtract` 的接口，但我暂时没有使用过它们复现工作流。

视频展示：


# 🕹️ DuolinGal

DuolinGal 是一套面向 KiriKiri Z galgame 的本地优先研究工具链。  
它把“资源提取 -> 台词对齐 -> 角色数据集导出 -> GPT-SoVITS 训练/量产 -> 游戏补丁回灌”串成了一条可复现的工程工作流，适合做：

- 英文配音补丁
- 中文配音补丁
- 角色级 TTS 研究与批量验证

当前项目已经在《千恋＊万花》上跑通：

- 资源提取与脚本反编译
- 台词与语音对齐
- 角色数据集导出
- GPT-SoVITS 单角色训练
- 多角色夜量产
- 批量 `wav -> ogg` 回灌
- 游戏内 `unencrypted/` 覆盖与 `patch-build` 重建
- 最终 `.xp3` 补丁打包并发布

## 🎯 项目目标

DuolinGal 是一条已经工程化的工作流。它解决的核心问题是：

1. 把 galgame 里的文本、语音、角色拆成可训练数据
2. 让 GPT-SoVITS 在 Windows 单卡环境下稳定训练与批量推理
3. 把生成结果重新整理成游戏可直接覆盖的语音树
4. 为最终的英文语音补丁打包

## 🌟 当前能力

- 分析游戏目录，识别 KiriKiri Z 常见特征
- 初始化可复现的项目工作区
- 解包（需要手动操作）
- 调用外部工具反编译 `.scn` / `.psb`
- 构建 `lines.csv` 与脚本节点索引
- 导出角色级 TTS 训练数据集
- 生成 GPT-SoVITS 训练清单与英文预览
- 生成单角色 GPT-SoVITS 训练工作区
- 生成并执行可恢复的多角色 GPT-SoVITS 量产队列
- 批量把生成语音转成游戏覆盖用 `.ogg`
- 重建项目级 `patch-build`
- 打包 `.xp3` 补丁

## 🚀 快速开始

### 0. 准备外部依赖

在开始之前，请先确认下面几样东西已经可用：

- `GARbro`
  当前已验证的主线是手动解包 `scn.xp3` 和 `voice.xp3`
- `FreeMote`
  用于反编译脚本资源
- `FFmpeg`
  用于音频格式转换
- `KirikiriTools`
  用于最终 `patch2.xp3` 打包
- 本地 `GPT-SoVITS` 仓库
- `GPTSoVits` conda 环境

> 当前真正复现成功的路径是：**手动解包 + DuolinGal 构建项目 + 本地 GPT-SoVITS 训练/量产**。  
> `prepare-krkrdump` / `KrkrExtract` 相关入口仍然保留，但未复现。

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

目前没有成功复现自动解包，总是显示 `Steam Error Application load error`，因此可以不填写解包工具路径（`krkrdump` `krkrextract`），直接手动解包游戏资源到指定目录即可。

### 3. 初始化项目并导出角色数据

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "<GAME_DIR>"
python -m duolingal init-project "<GAME_DIR>" --project-id senren-banka

# 由于自动化解包我没有复现成功，这里不用命令，用 GARbro 或其他解包工具做：
# 1. 把 scn.xp3 解到   "<PROJECT_ROOT>\extracted_script"
# 2. 把 voice.xp3 解到 "<PROJECT_ROOT>\extracted_voice"

python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal decompile-scripts "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal build-lines "<PROJECT_ROOT>"
python -m duolingal export-dataset "<PROJECT_ROOT>" "<PROJECT_ROOT>\extracted_voice"
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>"
```

跑到这里为止，你已经完成了：

- 项目初始化
- 脚本与语音资源导出
- 角色级训练清单与英文预览生成

接下来请按目标进入下面三条路径之一。

## 按目标选择路径

### A. 单角色验证

如果你想先验证某个角色能不能训出来、听起来像不像原角色，当前推荐顺序是：

```text
prepare-gptsovits-train
  -> run-prepare-all.ps1
  -> run-train-gpt.ps1
  -> run-train-sovits.ps1
  -> 准备英文批次
  -> 本地试听 / 回灌游戏
```

先生成单角色训练工作区：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-train "<PROJECT_ROOT>" --speaker "<SPEAKER_NAME>"
```

然后进入生成出来的：

- `tts-training/<EXPERIMENT_NAME>/scripts/`

按顺序运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-prepare-all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-train-gpt.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-train-sovits.ps1
```

可以看看这些文档：

- [GPT-SoVITS Training Guide](docs/gptsovits-training.zh-CN.md)
- [GPT-SoVITS Local Runbook](docs/gptsovits-local-runbook.zh-CN.md)
- [GPT-SoVITS Batch Guide](docs/gptsovits-batch.zh-CN.md)
- [GPT-SoVITS Reinject Guide](docs/gptsovits-reinject.zh-CN.md)

### B. 多角色量产

如果你已经不只是验证单角色，而是要顺序训练多个角色并批量生成英文语音，当前推荐顺序是：

```text
prepare-gptsovits-production
  -> run-gptsovits-production
  -> 每角色自动执行：
     前处理 -> GPT -> SoVITS -> 切权重 -> 推理 -> wav -> ogg
  -> 合并总覆盖树
  -> 重建 patch-build
  -> 可选同步到真实游戏目录
```

先准备一条量产计划：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" --sync-game-root
```

如果只想排部分角色：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" `
  --speaker "ムラサメ" `
  --speaker "芳乃" `
  --speaker "茉子"
```

然后运行：

```powershell
$env:PYTHONPATH='src'
python -m duolingal run-gptsovits-production "<PROJECT_ROOT>\tts-production\all-cast-v1"
```

或者直接执行生成出来的：

- `tts-production/<PLAN_NAME>/scripts/run-production.ps1`

如果某些角色需要固定锚点，或某些角色暂时应排除在量产队列外，请在项目根目录放：

- `tts-production/production-overrides.json`

多角色量产的详细说明看：

- [GPT-SoVITS Production Guide](docs/gptsovits-production.zh-CN.md)

### C. 最终清理与正式发布

量产跑完以后，不要直接删原始成果。当前正确顺序是：

```text
run-gptsovits-production
  -> prepare-final-cleanup
  -> 审核 cleanup-review.ready.csv
  -> 在副本上删除不该覆盖原音的 .ogg
  -> rebuild-patch-from-clean-copy.ps1
  -> patch-build/pack-patch2.ps1
  -> patch2.xp3
```

先生成安全副本：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-final-cleanup "<PROJECT_ROOT>"
```

然后在：

- `tts-release/final-cleanup-v1/review/cleanup-review.ready.csv`

里只把你确认应当回退原日语的行标成 `remove`。  
接着运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<PROJECT_ROOT>\tts-release\final-cleanup-v1\scripts\apply-reviewed-removals.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "<PROJECT_ROOT>\tts-release\final-cleanup-v1\scripts\rebuild-patch-from-clean-copy.ps1"
```

最后进入：

- `<PROJECT_ROOT>\patch-build`

执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\pack-patch2.ps1
```

得到最终的：

- `<PROJECT_ROOT>\patch-build\patch2.xp3`

## GPT-SoVITS 量产队列实际会做什么

当前仓库已经支持一条 **可恢复** 的多角色量产队列，流程如下：

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

## 关于“纯语气句保留原音”的策略

当前仓库已经支持基础保护：

- 纯标点英文在批次准备阶段会被跳过
- 个别被 `/tts` 判为无效文本的句子会被记录并跳过

但更强的“纯语气/弱句保留原音”规则，当前建议放到**整轮量产结束之后**做最后收尾，而不是提前加进跑主线。

原因是：

- 过早做强过滤，容易误删本来已经生成得不错的英文语音
- 量产先跑完，才能保住尽可能完整的第一版成果
- 最后如果删掉某些 `.ogg`，游戏会自然回退到原始日语语音

当前更推荐的顺序是：

1. 先完成整轮训练、推理、转码、覆盖树构建
2. 运行 `prepare-final-cleanup`，生成一份安全副本
3. 审核 `cleanup-review.ready.csv`
4. 再在副本上清理纯语气句、叫声、拟声句
5. 用清理后的副本重建 `patch-build`
6. 最后把清理后的副本用于正式 release 打包

对应命令是：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-final-cleanup "<PROJECT_ROOT>"
```

## 📃 文档导航

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

如果你只是按上面的 CLI 工作流复现项目，可以先跳过本节。  
本地 API 更适合你准备自己包一层界面或服务时再用。

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

## 📁 仓库结构

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
- 多角色量产可以持续推进
- 可以在安全副本上做最终弱句清理并回退原音
- 生成语音可以真正回灌到游戏里体验

没有解决：

- 专有名词发音词典，比如角色名总是被英语自然拼读，而不是正确的日语发音
- 最佳 epoch 自动搜索
- 弱句/拟声句的最终判定仍然需要人工审核，当前不建议前置自动强过滤

所以当前更适合把 DuolinGal 看成：

- 一条已经打通的 **工程化研究工作流**
- 一个能持续产出成果的 **本地量产入口**

## License
[MIT License](LICENSE)
