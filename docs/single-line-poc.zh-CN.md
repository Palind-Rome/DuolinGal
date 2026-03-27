# 单句 PoC 指南

这一步只做全年龄内容，不碰 `adult.xp3`、`adult2.xp3`。

## 目标

从已经构建好的 `lines.csv` 中挑出一条同时满足下面条件的台词：

- 有说话人
- 有日文和英文文本
- 有语音文件名
- 语音文件已经存在于你本地提取的 `voice/` 目录

然后在项目工作区里生成一套可用于单句替换测试的目录：

- `original/`
- `game-ready/unencrypted/`
- `metadata.json`
- `README.zh-CN.md`

## 命令

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-poc "<PROJECT_ROOT>" "<VOICE_DIR>"
```

如果你想限定角色或文本，也可以加过滤：

```powershell
python -m duolingal prepare-poc "<PROJECT_ROOT>" "<VOICE_DIR>" --speaker "芳乃"
python -m duolingal prepare-poc "<PROJECT_ROOT>" "<VOICE_DIR>" --contains "Good morning"
python -m duolingal prepare-poc "<PROJECT_ROOT>" "<VOICE_DIR>" --line-id "scene001-0001"
```

## 产物

命令会在项目目录下创建：

```text
<PROJECT_ROOT>/poc/<LINE_ID>/
|-- original/
|   `-- <VOICE_FILE>
|-- game-ready/
|   `-- unencrypted/
|       `-- <VOICE_FILE>
|-- metadata.json
`-- README.zh-CN.md
```

说明：

- `original/` 里是原始提取语音的备份拷贝。
- `game-ready/unencrypted/` 里是给你替换成英文 TTS 的目标文件位。
- `metadata.json` 记录这条台词的说话人、文本、语音文件名和路径。

## 你接下来手动要做的事

1. 把 `game-ready/unencrypted/` 里的那条语音替换成你自己的英文 `.ogg`。
2. 在本地实验目录中放入 `KirikiriTools` 的 `version.dll`。
3. 把生成好的 `unencrypted/` 目录放到游戏根目录。
4. 启动游戏并跳到那一句，确认是否成功播放替换后的语音。

## 为什么先做这个

这一步的价值不是“完成整作英配”，而是先验证三件事：

- 这一作的语音路径能不能被覆盖
- 你的英文音频格式是否被游戏接受
- `version.dll + unencrypted` 这条回灌链是否成立

单句成功以后，再去做批量替换和 `patch2.xp3` 会稳得多。
