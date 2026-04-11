# 路径与目录假设清单

这份文档记录 DuolinGal 当前仍然存在的“默认目录结构”“默认文件名”“默认相对位置”假设。

它不是问题清单，而是一份现状说明：

- 这些假设帮助我们把《千恋万花》的真实链路快速跑通
- 它们显著降低了排障成本
- 但也意味着：如果以后要做 GUI、多机器迁移、更通用的 CLI、或更泛化的项目支持，就值得继续参数化

当前状态和最早写这份笔记时相比已经有了明显变化：

- GPT-SoVITS 单角色训练链已经跑通
- 12 个角色的夜间量产已经跑通
- 最终清理已经切换成“先复制一份安全副本，再人工审核删除”的收尾策略

因此，本文会同时记录：

- 哪些路径假设仍然是仓库设计的一部分
- 哪些是当前阶段有意保留的工程折中
- 哪些在未来更适合改造成配置项

## 1. 仓库级默认路径

### 1.1 `REPO_ROOT` 推断

文件：
- `src/duolingal/config.py`

当前实现：
- `REPO_ROOT = Path(__file__).resolve().parents[2]`

含义：
- 默认把 `src/duolingal/...` 的上两级视为仓库根目录

影响：
- 这是“代码位置决定仓库根目录”的约定
- 如果未来包结构明显变化，这种推断也需要一起调整

### 1.2 默认工作区根目录

文件：
- `src/duolingal/config.py`

当前实现：
- `WORKSPACE_ROOT = REPO_ROOT / "workspace"`
- `PROJECTS_ROOT = WORKSPACE_ROOT / "projects"`

含义：
- 默认项目工作区落在 `<REPO_ROOT>/workspace/projects/`

影响：
- 当前 `init-project`、manifest、日志、提取结果、量产产物都围绕这个结构展开
- 以后如果做 GUI，比较适合改成用户可配置

### 1.3 默认工具链配置文件

文件：
- `src/duolingal/core/tool_config.py`

当前实现：
- `DEFAULT_TOOLCHAIN_CONFIG_PATH = REPO_ROOT / "configs" / "toolchain.local.json"`

含义：
- 默认工具链配置文件叫 `configs/toolchain.local.json`

影响：
- 现在已经支持用 `DUOLINGAL_TOOLCHAIN_CONFIG` 环境变量或显式参数覆盖
- 但默认值本身仍然是仓库内固定位置

## 2. 项目工作区默认布局

### 2.1 固定子目录集合

文件：
- `src/duolingal/config.py`
- `src/duolingal/core/workspace.py`

当前默认子目录：
- `raw_assets/`
- `extracted_voice/`
- `extracted_script/`
- `decompiled_script/`
- `dataset/`
- `models/`
- `generated_voice/`
- `release/`
- `logs/`

含义：
- `init-project` 会自动创建这一组目录

影响：
- 当前 CLI、preflight、parser、extractor 都依赖这些目录名
- 这是“项目内标准布局”的核心假设之一

## 3. 资源提取与脚本处理约定

### 3.1 XP3 包名到输出目录的固定映射

文件：
- `src/duolingal/core/extractor.py`

当前实现：
- `voice.xp3 -> extracted_voice/`
- `scn.xp3 -> extracted_script/`

含义：
- 当前抽取链路默认只对这两个资源包做了显式目录映射

影响：
- 对《千恋万花》这条链路是合适的
- 如果未来扩展到别的资源包类型，需要把映射设计做得更通用

### 3.2 脚本反编译默认输入/输出目录

文件：
- `src/duolingal/core/decompiler.py`
- `src/duolingal/core/parser.py`
- `src/duolingal/core/preflight.py`

当前约定：
- 默认从 `extracted_script/` 读取原始脚本资源
- 默认把反编译 JSON 写到 `decompiled_script/`
- `build-lines` 优先读 `decompiled_script/`，再退回 `extracted_script/`

影响：
- 这让流水线更直观
- 但也说明“脚本处理目录名”目前是固定的

## 4. 补丁、PoC、数据集与量产目录约定

### 4.1 补丁 staging 目录

文件：
- `src/duolingal/core/patching.py`
- `src/duolingal/core/gptsovits_reinject.py`
- `src/duolingal/core/final_cleanup.py`

当前约定：
- 默认补丁工作目录是 `<PROJECT_ROOT>/patch-build/`

补充说明：
- 量产完成后也会重建项目级 `patch-build/patch2`
- 最终收尾阶段则会从“清理副本”重新构建一次 `patch2`

### 4.2 单句 PoC 目录

文件：
- `src/duolingal/core/poc.py`

当前约定：
- 默认验证目录是 `<PROJECT_ROOT>/poc/<LINE_ID>/`

### 4.3 角色数据集目录

文件：
- `src/duolingal/core/dataset_export.py`
- `src/duolingal/core/gptsovits_prep.py`
- `src/duolingal/core/gptsovits_batch.py`

当前约定：
- 默认角色数据集根目录是 `<PROJECT_ROOT>/tts-dataset/`

影响：
- GPT-SoVITS 训练清单、批次准备、预览导出都围绕它组织

### 4.4 GPT-SoVITS 回灌目录

文件：
- `src/duolingal/core/gptsovits_reinject.py`

当前约定：
- 单条回灌验证目录会建在 `poc/gptsovits-*`
- 同时仍会准备 `patch-build/` 下的补丁 staging

### 4.5 全角色量产目录

文件：
- `src/duolingal/core/gptsovits_production.py`

当前约定：
- 量产计划默认建在 `<PROJECT_ROOT>/tts-production/<PLAN_NAME>/`

主要子目录：
- `scripts/`
- `logs/`
- `game-ready/unencrypted/`
- `production-state.json`
- `production-status.txt`

含义：
- 这是当前全角色训练、推理、转码、合并覆盖树的主工作区

### 4.6 最终清理副本目录

文件：
- `src/duolingal/core/final_cleanup.py`

当前约定：
- 最终清理默认建在 `<PROJECT_ROOT>/tts-release/<CLEANUP_NAME>/`

主要子目录：
- `source/unencrypted/`
- `review/`
- `scripts/`

含义：
- 最终“弱句/纯语气句保留原音”不是直接改量产成果
- 而是先复制一份安全副本，再在副本上人工审核和删除

## 5. GPT-SoVITS 训练专属路径假设

### 5.1 默认从 `tts-dataset` 读角色训练数据

文件：
- `src/duolingal/core/gptsovits_training.py`

当前实现：
- `resolved_project_root / "tts-dataset"`

含义：
- `prepare-gptsovits-train` 默认直接从当前项目的 `tts-dataset/` 里找角色数据

### 5.2 训练工作区默认写到 `tts-training`

文件：
- `src/duolingal/core/gptsovits_training.py`

当前实现：
- `training_root = resolved_project_root / "tts-training" / experiment_name`

含义：
- 每个角色/实验都会在 `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/` 下生成整套工作区

### 5.3 ASCII 安全音频镜像目录

文件：
- `src/duolingal/core/gptsovits_training.py`

当前实现：
- `staged_audio_root = training_root / "source-audio"`

含义：
- 为了绕开 Windows 上日文路径编码问题，训练前会额外生成一份 ASCII 友好的音频镜像目录

补充说明：
- 这不是替代原始音频目录
- 而是为官方训练脚本提供一个更稳定的读取入口

### 5.4 GPT-SoVITS 根目录自动推断

文件：
- `src/duolingal/core/gptsovits_training.py`

当前实现：
- `_resolve_gpt_sovits_root(...)`
- 未显式传入 `--gpt-sovits-root` 时，会先尝试读取 `toolchain.local.json` 里的
  `gpt-sovits.path`，再回退到按仓库相对位置推断 `../tools/GPT-SoVITS`

这就是典型的“位置硬编码”之一。

### 5.5 生成出来的脚本会写绝对路径

文件：
- `src/duolingal/core/gptsovits_training.py`

当前行为：
- 会为当前项目生成：
  - `run-prepare-*.ps1`
  - `run-train-*.ps1`
  - `train-gpt-launcher.py`
  - `train-sovits-launcher.py`
- 这些生成物里会写入当前机器可直接运行的绝对路径

说明：
- 这不是“仓库源码里手写死用户私有路径”
- 而是“源码里有模板，生成时把当前项目路径渲染进去”
- 当前阶段这样做有利于复现和排障

## 6. 编码与 Windows 兼容假设

### 6.1 UTF-8 文本读写是默认前提

当前经验：
- Windows PowerShell 5 下，如果不显式指定 UTF-8，中文和日文经常会在终端显示成乱码

因此：
- 文本文件、CSV、JSON、状态文件现在默认按 UTF-8 处理
- 在 PowerShell 里直接读文本时，通常应显式指定 `-Encoding UTF8`

### 6.2 Unicode 路径对部分音频工具不稳定

当前经验：
- Windows 下的某些 Python 音频库和外部工具，对日文路径支持并不稳定

因此现在保留了两类工程折中：
- 训练前生成 ASCII 安全的 `source-audio/`
- 批量 `wav -> ogg` 时必要时通过 ASCII 临时中转目录转换

这属于“稳定性补丁”，不是最终理想形态。

## 7. 当前故意保留的，和以后更适合参数化的

### 当前故意保留的

- 统一的项目目录布局
- 统一的 `tts-dataset/`、`tts-training/`、`tts-production/`、`tts-release/`、`patch-build/`、`poc/` 约定
- GPT-SoVITS 训练工作区里的绝对路径生成
- 按项目内约定自动推断工具链和工作区位置

原因：
- 当前阶段最重要的是复现和排障效率
- 路径固定后，很多问题更容易定位

### 以后更适合参数化的

- 工作区根目录
- 默认项目根目录
- `toolchain.local.json` 默认位置
- `tts-dataset/` 输出根目录
- `tts-training/` 输出根目录
- `tts-production/` 输出根目录
- `tts-release/` 输出根目录
- `patch-build/` 输出根目录
- `poc/` 输出根目录
- `GPT-SoVITS` 本地仓库根目录

## 8. 面向未来 GUI / 更通用 CLI 的建议

如果以后做 Web GUI 或更通用的 CLI，比较自然的演进方向是：

- 把这些路径放进项目设置
- 或放进用户级配置，而不是只依赖仓库相对位置
- 生成脚本时尽量减少绝对路径数量
- 长期看，把更多“工作区生成逻辑”改成参数化 runner，而不是项目专用脚本
- 把“最终清理副本”“量产计划”“补丁打包”都做成显式的、可复用的配置流程

## 9. 当前仍值得继续记录的问题

- Windows 上外部工具和 Python 环境仍然容易出现编码、依赖、运行时差异
- 最终“弱句/纯语气句保留原音”的筛选仍然需要人工复核，暂时不适合完全自动删除
- 最佳 epoch、停止时机、人工 QA 标准仍然主要依靠经验判断
- 生成音频的响度、风格一致性和角色一致性还缺自动化 QA
- 当前量产已经跑通，但正式 release 仍然需要“最终清理副本 -> QA -> 打包”这条收尾流程
