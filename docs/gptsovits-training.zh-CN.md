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

可选参数：

- `--gpt-sovits-root "<GPT_SOVITS_DIR>"`
- `--gpu 0`
- `--full-precision`
- `--gpt-epochs 12`
- `--sovits-epochs 20`
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

当前仓库在 GPT 第一阶段训练上，默认生成的是：

- `scripts/train-gpt-launcher.py`

这是一个 Windows-safe 单卡 launcher。它和直接调用官方 `s1_train.py` 的区别是：

- 保留相同的模型、配置、数据和权重路径
- 在 Windows 单卡环境下改用更稳的单卡训练方式
- 不再强行走单卡 DDP
- 关闭会触发控制台编码问题的 Rich 动态进度条
- 改为输出纯文本训练进度

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

它不负责：

- 自动安装 GPT-SoVITS 全部依赖
- 自动下载全部外部模型
- 自动评估“哪一轮最像角色本人”

## 已知限制与后续改进

当前这套训练工作区是“项目级生成脚本”思路，而不是“全局可移植 runner”思路。
这意味着：

- 生成出来的 `run-prepare-*.ps1`、`run-train-*.ps1`、`train-gpt-launcher.py`
  都会写入当前项目、当前机器可直接执行的绝对路径
- `prepare-gptsovits-train` 在未显式传入 `--gpt-sovits-root` 时，会按当前仓库结构推断
  `../tools/GPT-SoVITS`

这在当前本地研究流程里是合理的，但后续如果进入更通用的产品阶段，应当逐步改成：

- 允许用户在 CLI / Web GUI 中手动设置 GPT-SoVITS 根目录
- 支持把工具路径保存为项目配置或用户级配置，而不是只靠目录推断
- 让训练脚本尽量减少绝对路径硬编码，改成更参数化的启动方式

当前仍然存在、值得后续继续处理的问题包括：

- GPT-SoVITS 本地安装在 Windows 上仍有环境差异，部分依赖和运行时数据需要手工补齐
- 当前仓库已经验证了 GPT 第一阶段在 Windows 单卡上的稳定启动，但 SoVITS 阶段仍需要完整实测闭环
- 训练停止条件、最佳 epoch 选择、试听回归判断，目前主要依赖人工判断
- 生成语音的响度、语气稳定性、角色一致性，还没有完全自动化的 QA 规则
- Web GUI 还没有落地，当前仍然偏向本地脚本工作流
