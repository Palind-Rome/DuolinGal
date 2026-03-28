# GPT-SoVITS 英文合成批次准备

这一步的目标是：

- 从某个角色的 `preview_en.csv` 里挑出前几句英文台词
- 固定一条日语参考音频和参考文本
- 生成一套可直接喂给 GPT-SoVITS `api_v2.py` 的本地批次目录

## 为什么要单独做批次准备

前一阶段的 `prepare-gptsovits` 只解决训练清单。

但真正开始英文合成时，我们还需要一份更具体的内容：

- 哪几句先试
- 参考音频是哪句
- 参考日文是什么
- 输出文件应该保存到哪里

所以这里把“训练准备”和“英文试合成”拆开。

## 参考依据

GPT-SoVITS 官方仓库里有两条直接相关的信息：

1. 官方 README 提供了安装脚本和环境准备方式  
2. 官方 `api_v2.py` 使用 `/tts` 接口接收 JSON 请求，核心字段包括：
   - `text`
   - `text_lang`
   - `ref_audio_path`
   - `prompt_text`
   - `prompt_lang`
   - `media_type`

官方仓库：
[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)

## 命令

以丛雨为例，先取前 10 句：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10
```

如果你想强制指定参考台词，也可以：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10 --prompt-line-id "001・アーサー王ver1.07.ks-0549"
```

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

`requests.jsonl`

- 每行一条请求
- 里面已经包含 GPT-SoVITS `api_v2.py` 需要的请求体

`requests.csv`

- 方便人工检查
- 能看到：
  `line_id / jp_text / en_text / source_audio_path / output_path`

`invoke_api_v2.ps1`

- 假定你已经启动本机 `api_v2.py`
- 默认请求地址是 `http://127.0.0.1:9880/tts`
- 会逐条请求并把输出写到 `outputs/`

## 当前策略

这一步默认：

- 保留原始参考音频
- 用同一条日语参考音频驱动一小批英文句子
- 先输出 `wav`

之所以先输出 `wav`，只是为了更容易试听和排查。
确认英文结果可用之后，再转成 `.ogg` 回灌游戏更稳。
