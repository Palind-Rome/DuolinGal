# 数据集导出指南

当 `lines.csv` 已经构建完成，且你已经有全年龄 `voice/` 目录时，就可以把它们整理成按角色分组的 TTS 训练数据集。

## 目标

导出结果会满足下面几件事：

- 每个角色一个目录
- 每个目录里有 `audio/`
- 每个目录里有 `metadata.csv`
- 只保留“有说话人 + 有日文文本 + 能在 `voice/` 找到音频”的记录

## 命令

```powershell
$env:PYTHONPATH='src'
python -m duolingal export-dataset "<PROJECT_ROOT>" "<VOICE_DIR>"
```

如果你只想导出某个角色：

```powershell
python -m duolingal export-dataset "<PROJECT_ROOT>" "<VOICE_DIR>" --speaker "芳乃"
```

如果你想忽略样本太少的角色：

```powershell
python -m duolingal export-dataset "<PROJECT_ROOT>" "<VOICE_DIR>" --min-lines 50
```

## 产物

```text
<PROJECT_ROOT>/tts-dataset/
|-- <speaker-slug>/
|   |-- audio/
|   |   `-- *.ogg
|   `-- metadata.csv
`-- ...
```

`metadata.csv` 包含：

- `line_id`
- `scene_id`
- `order_index`
- `speaker_name`
- `voice_file`
- `audio_path`
- `jp_text`
- `en_text`

## 当前边界

- 这一步默认只使用你传入的 `voice/` 目录
- 当前建议继续只走全年龄路径
- `adult.xp3 / adult2.xp3` 仍然不纳入主线

## 为什么先做这个

因为这一步直接服务于你最初的项目目标：

- 角色原声数据能不能自动整理出来
- 每条语音是否能带上文本
- 后续能不能喂给 GPT-SoVITS 之类的模型

有了这个导出层，后面接 TTS 就不会还是手工搬文件了。
