# GPT-SoVITS 量产队列指南

这份文档说明的是：如何把多个角色串成一条 **可恢复、可夜跑** 的 GPT-SoVITS 队列，让它顺序执行：

1. 角色训练工作区准备
2. 前处理
3. GPT 训练
4. SoVITS 训练
5. 目标语言批量推理
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

先准备一条量产计划。

默认不传 `--target-language` 时，会生成英文计划，计划目录通常叫：

- `tts-production/all-cast-v1`

如果你想跑简体中文：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" --target-language zh-cn
```

如果 `configs/toolchain.local.json` 里已经配置了 `gpt-sovits.path` 指向本地 `api_v2.py`，这里会自动读取对应仓库根目录；也可以传 `--config "<CONFIG_PATH>"` 指向另一份配置，或者传 `--gpt-sovits-root "<GPT_SOVITS_DIR>"` 直接覆盖。

如果只想排部分角色，可以重复传 `--speaker`：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" `
  --speaker "ムラサメ" `
  --speaker "芳乃" `
  --speaker "茉子" `
  --target-language zh-cn
```

准备完成后，再运行：

```powershell
$env:PYTHONPATH='src'
python -m duolingal run-gptsovits-production "<PROJECT_ROOT>\tts-production\all-cast-zh-cn-v1"
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
- `--target-language`
  目标语言，支持 `en`、`zh-cn`、`zh-tw`。
- `--inference-limit`
  可选；限制每个角色最多推理多少条目标语言句子。
- `--sync-game-root`
  队列跑完后，把合并好的 OGG 覆盖树同步到真实游戏目录的 `unencrypted/`。
- `--gpt-epochs`
  默认 `12`。
- `--sovits-epochs`
  默认 `6`。这是当前基于《千恋万花》丛雨实测得到的更实用停点。

## 项目本地 overrides

如果某个项目里你已经知道：

- 某些角色应当使用固定锚点
- 某些角色暂时不该进量产队列

可以在项目根目录下放：

- `tts-production/production-overrides.json`

格式示例：

```json
{
  "exclude_speakers": ["白狛"],
  "speaker_prompt_line_ids": {
    "レナ": "006・レナ登場ver1.03.ks-0436",
    "廉太郎": "001・アーサー王ver1.07.ks-0346"
  }
}
```

说明：

- `exclude_speakers`
  这些角色会在量产队列里被直接跳过
- `speaker_prompt_line_ids`
  这些角色在批量推理时会优先使用指定 `line_id` 作为锚点参考句

这个文件是**项目本地配置**，适合记录像《千恋万花》这种作品里经过人工试听确认的 anchor 选择。

## 生成结果

`prepare-gptsovits-production` 至少会生成：

- `tts-production/<PLAN_NAME>/production-plan.json`
- `tts-production/<PLAN_NAME>/scripts/run-production.ps1`
- `tts-production/<PLAN_NAME>/README.zh-CN.md`
- `tts-production/<PLAN_NAME>/game-ready/unencrypted/`
- `tts-production/<PLAN_NAME>/logs/`

运行队列后，还会继续生成：

- `tts-production/<PLAN_NAME>/production-state.json`
- `tts-production/<PLAN_NAME>/production-status.txt`

如果推理已经开始，角色自己的批次目录下还会继续出现：

- `tts-dataset/<SPEAKER_NAME>/gptsovits/batches/<BATCH_NAME>/outputs/`
- `tts-dataset/<SPEAKER_NAME>/gptsovits/batches/<BATCH_NAME>/skipped-invalid-tts.jsonl`（仅在跳过坏句时生成）

## 队列实际做了什么

对每个角色，量产队列会顺序检查并执行：

1. 如果前处理产物缺失，则运行 `run-prepare-all.ps1`
2. 如果目标 GPT 权重缺失，则运行 `run-train-gpt.ps1`
3. 如果目标 SoVITS 权重缺失，则运行 `run-train-sovits.ps1`
4. 准备该角色的 GPT-SoVITS 目标语言批次
5. 启动或复用 `api_v2.py`
6. 切换到当前角色的 GPT / SoVITS 权重
7. 调用 `/tts` 批量合成
8. 把 `wav` 转成游戏覆盖用的 `.ogg`
9. 合并到总覆盖树

整条队列跑完后：

- 会用这棵总覆盖树重建项目级 `patch-build/<PLAN_NAME>/`
- 如果启用了 `--sync-game-root`，还会同步到真实游戏目录的 `unencrypted/`

说明：

- 最终游戏识别的补丁名仍然是 `patch2.xp3`
- 但不同计划现在会各自写到不同文件夹，例如：
  - `patch-build/all-cast-v1/patch2.xp3`
  - `patch-build/all-cast-zh-cn-v1/patch2.xp3`
- 最终清理后的 release 版本也同样会继续分目录，例如：
  - `patch-build/all-cast-v1-final-cleanup-v1/patch2.xp3`
  - `patch-build/all-cast-zh-cn-v1-final-cleanup-zh-cn-v1/patch2.xp3`

## 为什么叫“可恢复”

量产队列会维护：

- `production-state.json`

这个状态文件会记录已经完整完成的角色。中途中断后重新执行：

- 已完成的角色会跳过
- 未完成的角色会继续跑

同时还会维护一份更适合早上快速查看的人类可读摘要：

- `production-status.txt`

## 生产队列里的文本清洗保护

- 目标语言预览句如果在进入 GPT-SoVITS 前已经退化成“只有标点”的文本，比如 `......` 或 `.`
  现在会在批次准备阶段被自动跳过，不再送去 `/tts`。
- 如果仍然有个别句子在 GPT-SoVITS 内部进一步清洗后变成无效文本，生产队列会把它记到：
  - `batches/<BATCH_NAME>/skipped-invalid-tts.jsonl`
  然后跳过这单句，继续跑完整个角色和后续角色。
- `wav -> ogg` 转换在 Windows 下如果碰到 `libsndfile` / `ffmpeg` 直接读取日文路径失败，
  现在会先走一层 ASCII 临时中转，再继续转换。
- 也就是说，单条坏样本不应该再把整晚量产队列直接打断。

## 被跳过的句子会怎样

如果某句目标语言台词因为以下原因被跳过：

- 它本身退化成纯标点
- `/tts` 最终认定它不是有效文本

那么量产队列的行为是：

1. 不为这句生成新的目标语言 `.ogg`
2. 不把这条语音文件放进总覆盖树
3. 最终游戏里仍然播放原始日语语音

也就是说，当前策略不是“坏句也强行英配”，而是：

- **有可靠目标语言输出的句子才覆盖**
- **纯符号/超弱语气句默认保留原音**

这对《千恋万花》这类作品反而通常更稳，因为像 `……`、`!`、`……？` 这种语气音，本来就未必适合硬做目标语言 TTS。

## 关于“纯语气句保留原音”的当前策略

当前仓库已经支持：

- 纯标点目标文本在批次准备阶段直接跳过

但**更强的“弱句/纯语气句自动剔除”**，当前仍建议放在量产流程的最后做人工或半自动收尾，而不是现在就前置到整条夜跑队列里。

原因是：

- 前置规则如果太激进，容易误伤正常短句
- 而在回灌阶段再删除这些 `.ogg`，游戏会自然回退到原始日语语音

也就是说，当前更推荐：

1. 先把训练与批量推理跑完
2. 再对纯语气、叫声、拟声句做最终清理
3. 没被保留到补丁覆盖树里的句子，会继续播放原音

## ASCII 中转目录到底是什么

Windows 下这一轮实际踩到过的情况是：

- `soundfile/libsndfile` 读取日文路径失败
- 回退到 `ffmpeg` 后，`ffmpeg` 也可能直接拒绝这个日文路径

所以当前实现会在**目标输出目录附近**临时创建一个只含 ASCII 的中转目录，例如：

```text
tts-production/all-cast-zh-cn-v1/
`-- .gptsovits-ogg-<random>/
    |-- input.wav
    `-- output.ogg
```

流程是：

1. 把原始 `wav` 复制到这个 ASCII 临时目录
2. 在这里完成 `wav -> ogg`
3. 再把最终 `.ogg` 复制回正式覆盖树
4. 转换结束后删除这个临时目录

它只是一个**稳定性补丁**，不是新的长期产物目录。

## `production-status.txt` 里会写什么

里面会写：

- 当前总进度
- 当前角色
- 当前阶段
- 如果当前在训练或推理：
  - 当前 `epoch/batch` 或已完成句数
  - 当前阶段百分比
  - 已用时
  - 预计剩余时间
- 最近完成的几个角色

也就是说，它不是“一次性脚本”，而是一条可以分多晚推进的可恢复队列。

## 第二天起来先看什么

最推荐的顺序是：

1. 看 `production-status.txt`
   先判断停在哪个角色、哪个阶段、有没有 ETA。
2. 看 `production-state.json`
   确认已经完整完成了几个角色。
3. 看当前角色批次目录：
   - `outputs/` 里有多少 `wav`
   - 是否出现 `skipped-invalid-tts.jsonl`
4. 看 `game-ready/unencrypted/`
   确认已经有多少条真正进了总覆盖树。

如果终端停在某个角色的 `convert` 阶段，通常意味着：

- 该角色的大部分推理已经完成
- 但在 `wav -> ogg` 或总覆盖树写入这一层被打断

这时只要修掉对应的转换问题，再重跑同一条 `run-production.ps1` 即可。

## 当前默认训练策略

当前仓库默认使用：

- `GPT epochs = 12`
- `SoVITS epochs = 6`

这是基于当前《千恋万花》丛雨角色实测得出的第一轮工程默认值：

- `GPT e12`
- `SoVITS e6`

在这组权重下：

- 目标语言推理已经成功
- 回灌游戏已经成功
- 丛雨前 50 句已经成功生成并放进游戏体验

所以这条量产队列当前更偏向：

- 先稳定批量出“第一版可玩结果”
- 再按角色逐个微调更细的发音与听感

## 权重和量产产物要长期保留

建议长期保留这些目录：

- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/weights/gpt/`
- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/weights/sovits/`
- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/configs/`
- `<PROJECT_ROOT>/tts-production/<PLAN_NAME>/`

原因：

- 这些权重是你已经验证过的角色音色成果
- 以后如果做别的文本版本，不应该默认重训
- 量产目录里还包含角色批次、覆盖树、状态文件与日志，便于继续夜跑或回溯问题

如果以后想做中文版等其他语言版本，当前更推荐的默认顺序是：

1. 保留现有角色 GPT / SoVITS 权重
2. 准备新语言文本
3. 先直接用现有权重做新语言推理
4. 只有听感明显不够好时，再考虑补训或重训

## 最终弱句清理建议在副本上进行

虽然当前量产流程已经会跳过明显无效的文本，但更强的“纯语气句 / 叫声 / 拟声句保留原音”清理，仍建议放到**整轮量产结束之后**再做。

更稳的顺序是：

1. 先把整轮训练、推理、转码、覆盖树构建全部跑完
2. 复制一份：
   - `tts-production/<PLAN_NAME>/game-ready/unencrypted/`
   或
   - `patch-build/`
3. 在这个副本上清理不该目标语言覆盖的 `.ogg`
4. 用清理后的副本做最终 QA 和 release 打包

这样做的好处是：

- 不会误删已经生成得不错的目标语言语音
- 原始量产结果仍然完整保留
- 如果清理规则过猛，可以回滚到量产原件重新来

## 建议夜跑方式

1. 保持电脑插电
2. 关闭会抢 GPU 的程序和游戏
3. 优先使用 `GPTSoVits` conda 环境
4. 先准备好计划，再运行 `scripts/run-production.ps1`
5. 第二天优先看：
   - `production-state.json`
   - `production-status.txt`
   - `logs/`
   - `game-ready/unencrypted/`

整作全角色、全目标语言句子的训练和推理通常不会在一个短夜里全部完成，所以这条队列默认按照“可恢复”来设计。跑到哪一步都没关系，第二天继续执行同一份计划即可。

## 当前边界

这条量产队列解决的是：

- 多角色顺序训练
- 多角色顺序推理
- 合并覆盖树
- 项目级 patch staging 重建

它还没有解决：

- 专有名词发音词典
- 最佳 epoch 自动搜索
- 全自动听感 QA
- 每个角色独立的“是否继续加训”智能判断

所以当前更适合把它看成：

- 一个稳定的 **工程量产入口**
- 而不是最终完全无人值守的“自动配音导演”
