# GPT-SoVITS 训练清单准备

这一步的目标很窄：

- 复用已经导出的 `tts-dataset`
- 为每个角色生成 GPT-SoVITS 可直接读取的训练清单
- 同时保留一份英文预览映射，方便后续做合成与人工抽检

当前这一步**不会修改原始 galgame 音频**，也不会做：

- 重采样
- 改声道
- 改响度
- 裁静音

## 参考依据

DuolinGal 当前按 GPT-SoVITS 官方 README 里说明的标注格式准备训练清单：

`vocal_path|speaker_name|language|text`

官方仓库：
[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)

## 命令

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>"
```

只准备一个角色：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>" --speaker "ムラサメ"
```

如果你已经把数据集导到了别处，也可以手动指定：

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>" --dataset-root "<DATASET_ROOT>"
```

## 输出结构

每个角色目录下会新增一个 `gptsovits/`：

```text
tts-dataset/
`-- ムラサメ/
    |-- audio/
    |-- metadata.csv
    `-- gptsovits/
        |-- train_ja.list
        `-- preview_en.csv
```

`train_ja.list`

- 用于 GPT-SoVITS 训练
- 每行格式：
  `绝对音频路径|角色名|ja|日文台词`

`preview_en.csv`

- 用于后续英文合成与人工复核
- 保留：
  `line_id / speaker_name / jp_text / en_text / audio_path`

## 为什么先导出日文训练清单

因为我们当前目标是：

1. 用原始日语角色语音做角色音色训练
2. 后面再把同一批对齐好的英文文本拿来做英文生成

所以这一步先稳定输出：

- 日语训练输入
- 英文目标预览

这样比一开始就把训练、推理、补丁三件事绑死在一起更稳。
