# GPT-SoVITS 英文合成批次准备

这一步的目标是：

- 从某个角色的 `preview_en.csv` 里挑出一小批英文目标句
- 为每句目标句准备好 GPT-SoVITS `api_v2.py` 所需的 JSON 请求
- 生成一个可直接本地重跑、试听和回灌前 QA 的批次目录

## 为什么要单独做这一步

`prepare-gptsovits` 负责把角色数据整理成：

- `train_ja.list`
- `preview_en.csv`

但真正开始英文试听时，我们还需要再明确几件事：

- 先试哪几句英文
- 每句英文到底用哪条日语参考句
- 输出 WAV 放到哪里
- 如何一键把整批请求喂给 `api_v2.py`

所以这里把“训练数据准备”和“英文试听批次准备”拆开。

## 参考依据

GPT-SoVITS 官方 `api_v2.py` 的 `/tts` 请求体核心字段包括：

- `text`
- `text_lang`
- `ref_audio_path`
- `prompt_text`
- `prompt_lang`
- `media_type`

官方仓库：
[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)

## 命令

以丛雨为例，先准备前 10 句英文试听：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10 --reference-mode auto
```

如果你想强制指定一条锚点参考句，也可以加：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10 --prompt-line-id "<LINE_ID>" --reference-mode auto
```

## 三种参考模式

### `anchor`

整批英文句子都使用同一条日语参考句和参考音频。

优点：

- 最稳
- 最容易排查
- 适合第一次把链路跑通

缺点：

- 跨句语气恢复有限
- 不同英文句子更容易被同一个参考句“拉平”

### `per-line`

每句英文都使用它自己那一行的日语参考句和参考音频。

优点：

- 更容易把原句的语气、停顿和情绪带回来
- 很适合做“这句到底像不像原作语气”的对比试听

缺点：

- 如果某条日语参考本身太短、太弱，反而会让条件提示不稳定

### `auto`

优先使用每句自己的参考句；如果某句日语太短、太像语气词，就自动回退到锚点参考句。

这是当前最推荐的模式。

它适合你现在这种场景：

- 已经有单角色训练基座
- 希望尽量恢复原句语气
- 但又不想让 `えっ`、`うむ`、`……` 这种超短参考把结果带偏

## 为什么纯语气词可能不适合强行做参考句

即使已经训练出角色基座音色，参考句仍然会影响当前句子的：

- 韵律
- 停顿
- 情绪起伏
- 句尾落点

所以：

- “完整句子”通常更适合当参考句
- “纯语气词 / 超短感叹句”提供的韵律上下文太少
- 这类句子在 `per-line` 下有时会比 `anchor` 更不稳

也就是说，训练基座变强以后，“像谁说话”会更稳，但“这句怎么说”仍然会受参考句质量影响。

## 输出结构

命令会在角色目录下生成：

```text
tts-dataset/
`-- ムラサメ/
    `-- gptsovits/
        `-- batches/
            `-- first-10-en/
                |-- requests.jsonl
                |-- requests.csv
                |-- invoke_api_v2.ps1
                |-- README.zh-CN.md
                `-- outputs/
```

### `requests.jsonl`

- 每行一条 `/tts` 请求
- 可直接喂给 `api_v2.py`

### `requests.csv`

- 方便人工检查
- 会额外记录：
  - `prompt_line_id`
  - `prompt_audio_path`
  - `prompt_text`
  - `prompt_source`

其中：

- `prompt_source=self` 表示这句用了自己的参考句
- `prompt_source=anchor` 表示整批固定锚点
- `prompt_source=anchor-fallback` 表示在 `auto` 模式下因参考太短而回退到锚点

### `invoke_api_v2.ps1`

- 假定你已经启动本地 `api_v2.py`
- 默认向 `http://127.0.0.1:9880/tts` 发请求
- 逐条写出 WAV 到 `outputs/`

## 推荐用法

### 第一次跑通链路

先用：

```powershell
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10 --reference-mode anchor
```

### 训练后做中途试听

优先用：

```powershell
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10 --reference-mode auto
```

### 做单句精听对比

可以试：

```powershell
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10 --reference-mode per-line
```

## 当前边界

- 这一步只负责准备批次，不直接启动 GPT-SoVITS
- 默认先输出 `wav`，方便试听和排查
- 真正回灌进游戏前，仍建议先做一次人工 QA，再转成 `.ogg`
