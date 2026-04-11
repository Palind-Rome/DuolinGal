# GPT-SoVITS 训练指南

这份文档说明的是：如何把已经导出的角色语音数据，整理成 GPT-SoVITS 可训练格式，并在本地启动角色专属训练。

当前仓库针对《千恋万花》这类已经完成“语音 + 文本对齐”的项目，走的是一条偏工程化、偏稳定的路线：

- 不重新切片原始 galgame 语音
- 不默认做降噪、响度统一或静音裁切
- 先生成训练工作区
- 再调用本地 GPT-SoVITS 进行训练

## 适用前提

开始前应当已经完成：

- `export-dataset`
- `prepare-gptsovits`
- 本地 GPT-SoVITS 环境可用

角色数据集通常位于：

- `<PROJECT_ROOT>/tts-dataset/<SPEAKER_NAME>/`

训练工作区会生成到：

- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/`

## 仓库命令

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-train "<PROJECT_ROOT>" --speaker "<SPEAKER_NAME>"
```

如果 `configs/toolchain.local.json` 里已经配置了：

```json
"gpt-sovits": {
  "path": "E:/GPT-SoVITS/GPT-SoVITS-v2pro-20250604/api_v2.py"
}
```

那么命令会自动把这个 `api_v2.py` 路径解析回 GPT-SoVITS 仓库根目录。  
如果你想指定另一份配置文件，可以额外传 `--config "<CONFIG_PATH>"`；如果想直接覆盖配置，则传 `--gpt-sovits-root "<GPT_SOVITS_DIR>"`。

可选参数：

- `--config "<CONFIG_PATH>"`
- `--gpt-sovits-root "<GPT_SOVITS_DIR>"`
- `--gpu 0`
- `--full-precision`
- `--gpt-epochs 12`
- `--sovits-epochs 6`
- `--gpt-batch-size 4`
- `--sovits-batch-size 4`

## 生成结果

命令会生成一个完整训练工作区，至少包含：

- `inputs/train_ja.list`
- `configs/s1-v2.yaml`
- `configs/s2-v2.json`
- `scripts/run-prepare-stage1.ps1`
- `scripts/run-prepare-stage2.ps1`
- `scripts/run-prepare-stage3.ps1`
- `scripts/run-prepare-all.ps1`
- `scripts/train-gpt-launcher.py`
- `scripts/run-train-gpt.ps1`
- `scripts/run-train-sovits.ps1`
- `scripts/run-train-all.ps1`
- `README.zh-CN.md`

## 推荐顺序

1. 运行 `scripts/run-prepare-all.ps1`
2. 确认前处理产物已经生成
3. 运行 `scripts/run-train-gpt.ps1`
4. GPT 阶段稳定后，再运行 `scripts/run-train-sovits.ps1`

## 前处理阶段在做什么

`run-prepare-all.ps1` 会顺序调用 GPT-SoVITS 官方三步：

1. `1-get-text.py`
2. `2-get-hubert-wav32k.py`
3. `3-get-semantic.py`

它们分别负责：

- 生成文本/音素索引
- 生成 `32k wav` 与 HuBERT 特征
- 生成 semantic token

完成后，实验目录通常会出现：

- `2-name2text.txt`
- `4-cnhubert/`
- `5-wav32k/`
- `6-name2semantic.tsv`

这些文件位于：

- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/exp/<EXPERIMENT_NAME>/`

## 为什么训练前要“先处理”

GPT-SoVITS 训练时吃的不是“原始 OGG + 原始文本”。

它训练时真正依赖的是：

- 文本/音素
- HuBERT 特征
- semantic token

所以前处理的作用，是把 galgame 资源变成模型真正能读的训练数据。

## Windows 单卡训练说明

当前仓库在 Windows 单卡训练上，默认会生成：

- `scripts/train-gpt-launcher.py`
- `scripts/train-sovits-launcher.py`

这些都是 Windows-safe 单卡 launcher。它们和直接调用官方 `s1_train.py` / `s2_train.py` 的区别是：

- 保留相同的模型、配置、数据和权重路径
- 在 Windows 单卡环境下改用更稳的单卡训练方式
- 不再强行走单卡 DDP
- GPT 阶段关闭会触发控制台编码问题的 Rich 动态进度条
- 两个阶段都改为输出更容易追踪的纯文本训练进度

这样做的原因不是“改模型”，而是“让训练在 Windows 单卡上稳定跑起来”。

对单张 GPU 来说，这通常不会拖慢训练，反而能减少不必要的分布式开销。

## GPT 阶段会输出什么

运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-train-gpt.ps1
```

正常情况下，你会看到：

- `Training started: epochs=..., batches_per_epoch=...`
- `Epoch 1/12 started`
- 每隔固定 batch 的一条纯文本日志
- `Epoch 1/12 finished`

日志示例：

```text
Epoch 1 | batch 50/863 | global_step 12 | loss 393.4187 | acc 0.2766 | lr 0.002000
```

这说明训练已经真正进入了 batch 级推进，而不是只初始化了模型。

## GPT 阶段的主要产物

GPT 阶段主要关注两个位置：

- `exp/<EXPERIMENT_NAME>/logs_s1_v2/ckpt`
- `weights/gpt/`

通常：

- `ckpt/` 会保存训练过程中的 checkpoint
- `weights/gpt/` 会保存更方便后续调用的半精度权重

## SoVITS 阶段

GPT 阶段稳定后，再运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-train-sovits.ps1
```

这一阶段更偏“音色还原”，通常比 GPT 阶段更久。

建议在 GPT 阶段已经确认：

- 数据无明显问题
- 路径无误
- 日志与 checkpoint 正常增长

之后再开始 SoVITS。

## 当前经验默认值

当前仓库默认生成的训练工作区会使用：

- `GPT epochs = 12`
- `SoVITS epochs = 6`

这不是官方硬性推荐，而是基于当前《千恋万花》丛雨这轮本地实测得到的保守默认：

- GPT 在 `e12` 时已经稳定可用
- SoVITS 在 `e5 ~ e6` 左右就已经达到第一轮“主观听感满意”
- 再继续向 `e7+` 训练，收益未必明显，反而更值得警惕过拟合

所以如果你只是想先拿到一个可试听、可回灌、可继续迭代的角色模型，`12 + 6` 是一个更实用的起点。

如果后续换角色、换数据规模、换语言组合，也仍然建议：

- 先用这个保守默认值起步
- 再通过中途 checkpoint 试听决定是否继续加 epoch

## 训练完成后要保留什么

单角色训练完成后，至少建议长期保留：

- `weights/gpt/`
- `weights/sovits/`
- `configs/`
- `exp/<EXPERIMENT_NAME>/logs_s1_v2/`
- `exp/<EXPERIMENT_NAME>/logs_s2_v2/`

这些内容分别对应：

- 最终可推理权重
- 训练时使用的配置
- 训练期 checkpoint 与日志

如果这些目录保留下来，后续就不需要把同一个角色“从零重新训练一遍”。

## 如果以后想做中文版，还要重训吗

默认不建议一上来就重训。

对于已经训练完成的角色，当前更合理的顺序是：

1. 先保留现有 GPT / SoVITS 权重
2. 准备中文文本
3. 直接用现有角色权重做中文推理
4. 听完效果，再决定是否需要补训

原因是：

- 训练是高成本步骤
- 现有权重已经把角色音色学出来了
- 新语言版本往往先做推理验证，就能判断是否足够可用

只有在以下情况，才更值得考虑重训或补训：

- 中文听感明显不稳定
- 角色音色偏差明显
- 新语言中的断句、发音、韵律问题非常突出

## 设计原则

- 不修改原始 galgame 提取语音
- 训练工作区尽量使用 ASCII 友好路径，减少 Windows 编码问题
- 训练逻辑尽量复用官方 GPT-SoVITS
- 只在启动方式和 Windows 兼容层面做必要适配

## 当前边界

当前仓库解决的是：

- 训练工作区生成
- 前处理脚本生成
- GPT / SoVITS 启动脚本生成
- Windows 单卡下的 GPT 第一阶段稳定启动
- 基于这些单角色工作区继续生成可恢复的多角色量产队列

它不负责：

- 自动安装 GPT-SoVITS 全部依赖
- 自动下载全部外部模型
- 自动评估“哪一轮最像角色本人”

## 已知限制与后续改进

当前这套训练工作区是“项目级生成脚本”思路，而不是“全局可移植 runner”思路。
这意味着：

- 生成出来的 `run-prepare-*.ps1`、`run-train-*.ps1`、`train-gpt-launcher.py`
  都会写入当前项目、当前机器可直接执行的绝对路径
- `prepare-gptsovits-train` 在未显式传入 `--gpt-sovits-root` 时，会优先读取
  `toolchain.local.json` 里的 `gpt-sovits.path`；只有在配置里也没有时，才会按仓库结构推断
  `../tools/GPT-SoVITS`

这在当前本地研究流程里是合理的，但后续如果进入更通用的产品阶段，应当逐步改成：

- 允许用户在 CLI / Web GUI 中手动设置 GPT-SoVITS 根目录
- 支持把工具路径保存为项目配置或用户级配置，而不是只靠目录推断
- 让训练脚本尽量减少绝对路径硬编码，改成更参数化的启动方式

当前仍然存在、值得后续继续处理的问题包括：

- GPT-SoVITS 本地安装在 Windows 上仍有环境差异，部分依赖和运行时数据需要手工补齐
- 当前仓库已经验证了 GPT 第一阶段在 Windows 单卡上的稳定启动；SoVITS 阶段现在也会生成同类 launcher，但仍以本轮实际重跑结果为准
- 训练停止条件、最佳 epoch 选择、试听回归判断，目前主要依赖人工判断
- 生成语音的响度、语气稳定性、角色一致性，还没有完全自动化的 QA 规则
- 英文推理里的专有名词、角色名、日语罗马字词汇，目前还没有单独的发音词典或文本预处理规则；例如 `Murasame` 这类词，后续值得加入自定义 pronunciation / G2P 映射，避免模型按默认英语自然拼读去念
- Web GUI 还没有落地，当前仍然偏向本地脚本工作流

如果接下来要把这套流程继续扩成“多角色夜间顺序训练 + 推理”，请继续看：

- [GPT-SoVITS Production Guide](gptsovits-production.zh-CN.md)
