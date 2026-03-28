# GPT-SoVITS 训练准备指南

这一步的目标不是直接替你跑完训练，而是把某个角色的 GPT-SoVITS 官方训练工作区一次性准备好。

当前仓库已经支持为单个角色生成：

- 训练输入清单
- 官方 `prepare_datasets` 三步脚本
- GPT 训练脚本
- SoVITS 训练脚本
- 一份本地 README

## 适用前提

- 你已经完成：
  - `export-dataset`
  - `prepare-gptsovits`
- 本机已经有可运行的 GPT-SoVITS 安装目录
- 建议在已激活 `GPTSoVits` conda 环境的终端里执行后续本地脚本

## 仓库命令

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-train "<PROJECT_ROOT>" --speaker "<SPEAKER_NAME>"
```

可选参数：

- `--gpt-sovits-root "<GPT_SOVITS_DIR>"`
  当本机 GPT-SoVITS 不在默认推断位置时使用
- `--gpu 0`
  指定要用的 GPU 编号
- `--full-precision`
  关闭 half precision
- `--gpt-epochs 12`
- `--sovits-epochs 20`
- `--gpt-batch-size 4`
- `--sovits-batch-size 4`

## 生成结果

命令会在对应角色目录下生成一个本地训练工作区，里面至少包含：

- `inputs/train_ja.list`
- `configs/s1-v2.yaml`
- `configs/s2-v2.json`
- `scripts/run-prepare-stage1.ps1`
- `scripts/run-prepare-stage2.ps1`
- `scripts/run-prepare-stage3.ps1`
- `scripts/run-prepare-all.ps1`
- `scripts/run-train-gpt.ps1`
- `scripts/run-train-sovits.ps1`
- `scripts/run-train-all.ps1`
- `README.zh-CN.md`

## 推荐顺序

1. 先运行 `run-prepare-all.ps1`
2. 确认实验目录里已经出现：
   - `2-name2text.txt`
   - `4-cnhubert/`
   - `5-wav32k/`
   - `6-name2semantic.tsv`
3. 再运行 `run-train-gpt.ps1`
4. GPT 阶段稳定后再运行 `run-train-sovits.ps1`

## 设计原则

- 不修改原始 galgame 提取音频
- 训练实验目录尽量使用 ASCII 友好的名字，降低 Windows 路径编码风险
- 直接调用 GPT-SoVITS 官方脚本，不在仓库里重新发明训练器
