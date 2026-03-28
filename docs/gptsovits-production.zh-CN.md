# GPT-SoVITS 量产队列指南

这份文档说明的是：如何把多个角色串成一条 **可恢复、可夜跑** 的 GPT-SoVITS 队列，让它顺序执行：

1. 角色训练工作区准备
2. 前处理
3. GPT 训练
4. SoVITS 训练
5. 英文批量推理
6. `wav -> ogg`
7. 合并成总覆盖树，并重建 `patch-build`

这条队列的目标不是“最短时间内出一个 demo”，而是把当前已经在丛雨身上验证成功的流程，扩展成可以继续复用到其他角色的工程入口。

## 适用前提

开始前应当已经完成：

- 项目初始化与 `lines.csv` 构建
- 角色语音数据导出：`export-dataset`
- GPT-SoVITS 训练清单准备：`prepare-gptsovits`
- 本地 `GPT-SoVITS` 环境和 `GPTSoVits` conda 环境可用

## 仓库命令

先准备一条量产计划：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" --sync-game-root
```

如果只想排部分角色，可以重复传 `--speaker`：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" `
  --speaker "ムラサメ" `
  --speaker "芳乃" `
  --speaker "茉子"
```

准备完成后，再运行：

```powershell
$env:PYTHONPATH='src'
python -m duolingal run-gptsovits-production "<PROJECT_ROOT>\tts-production\all-cast-v1"
```

或者直接在生成目录里执行：

- `scripts/run-production.ps1`

## 关键参数

- `--speaker`
  只排指定角色；不传则默认把所有符合条件的角色都放进队列。
- `--min-lines`
  至少多少条已对齐样本才保留该角色。
- `--reference-mode`
  夜间推理时参考句策略，支持 `anchor`、`per-line`、`auto`。当前更推荐 `auto`。
- `--inference-limit`
  可选；限制每个角色最多推理多少条英文句子。
- `--sync-game-root`
  队列跑完后，把合并好的 OGG 覆盖树同步到真实游戏目录的 `unencrypted/`。
- `--gpt-epochs`
  默认 `12`。
- `--sovits-epochs`
  默认 `6`。这是当前基于《千恋万花》丛雨实测得到的更实用停点。

## 生成结果

`prepare-gptsovits-production` 至少会生成：

- `tts-production/<PLAN_NAME>/production-plan.json`
- `tts-production/<PLAN_NAME>/scripts/run-production.ps1`
- `tts-production/<PLAN_NAME>/README.zh-CN.md`
- `tts-production/<PLAN_NAME>/game-ready/unencrypted/`
- `tts-production/<PLAN_NAME>/logs/`

运行队列后，还会继续生成：

- `tts-production/<PLAN_NAME>/production-state.json`

## 队列实际做了什么

对每个角色，量产队列会顺序检查并执行：

1. 如果前处理产物缺失，则运行 `run-prepare-all.ps1`
2. 如果目标 GPT 权重缺失，则运行 `run-train-gpt.ps1`
3. 如果目标 SoVITS 权重缺失，则运行 `run-train-sovits.ps1`
4. 准备该角色的 GPT-SoVITS 英文批次
5. 启动或复用 `api_v2.py`
6. 切换到当前角色的 GPT / SoVITS 权重
7. 调用 `/tts` 批量合成
8. 把 `wav` 转成游戏覆盖用的 `.ogg`
9. 合并到总覆盖树

整条队列跑完后：

- 会用这棵总覆盖树重建项目级 `patch-build`
- 如果启用了 `--sync-game-root`，还会同步到真实游戏目录的 `unencrypted/`

## 为什么叫“可恢复”

量产队列会维护：

- `production-state.json`

这个状态文件会记录已经完整完成的角色。中途中断后重新执行：

- 已完成的角色会跳过
- 未完成的角色会继续跑

也就是说，它不是“一次性脚本”，而是一条可以分多晚推进的可恢复队列。

## 当前默认训练策略

当前仓库默认使用：

- `GPT epochs = 12`
- `SoVITS epochs = 6`

这是基于当前《千恋万花》丛雨角色实测得出的第一轮工程默认值：

- `GPT e12`
- `SoVITS e6`

在这组权重下：

- 英文推理已经成功
- 回灌游戏已经成功
- 丛雨前 50 句已经成功生成并放进游戏体验

所以这条量产队列当前更偏向：

- 先稳定批量出“第一版可玩结果”
- 再按角色逐个微调更细的发音与听感

## 建议夜跑方式

1. 保持电脑插电
2. 关闭会抢 GPU 的程序和游戏
3. 优先使用 `GPTSoVits` conda 环境
4. 先准备好计划，再运行 `scripts/run-production.ps1`
5. 第二天优先看：
   - `production-state.json`
   - `logs/`
   - `game-ready/unencrypted/`

整作全角色、全英文句子的训练和推理通常不会在一个短夜里全部完成，所以这条队列默认按照“可恢复”来设计。跑到哪一步都没关系，第二天继续执行同一份计划即可。

## 当前边界

这条量产队列解决的是：

- 多角色顺序训练
- 多角色顺序推理
- 合并覆盖树
- 项目级 patch staging 重建

它还没有解决：

- 专有名词英文发音词典
- 最佳 epoch 自动搜索
- 全自动听感 QA
- 每个角色独立的“是否继续加训”智能判断

所以当前更适合把它看成：

- 一个稳定的 **工程量产入口**
- 而不是最终完全无人值守的“自动配音导演”
