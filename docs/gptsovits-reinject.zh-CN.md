# GPT-SoVITS 回灌自动化

这个命令负责把单条 `GPT-SoVITS` 合成输出自动变成游戏可测试资源：

1. 读取某个批次目录下的 `outputs/*.wav`
2. 转成游戏更稳的 `Ogg Vorbis`
3. 自动命名成目标语音文件名
4. 自动生成 `unencrypted` 覆盖目录
5. 自动生成 `patch2` staging

## 命令

```powershell
python -m duolingal prepare-gptsovits-reinject "<PROJECT_ROOT>" "<BATCH_DIR>" --target-voice-file "<TARGET_VOICE_FILE>" --source-output-name "<OUTPUT_WAV_NAME>"
```

示例：

```powershell
python -m duolingal prepare-gptsovits-reinject "<PROJECT_ROOT>" "<PROJECT_ROOT>\tts-dataset\ムラサメ\gptsovits\batches\first-10-en" --target-voice-file "uts001_001.ogg" --source-output-name "mur001_001.wav"
```

## 重要说明

- 这个命令应当在装有 `soundfile` 和 `scipy` 的 Python 环境里运行
- 在当前项目实践里，最稳妥的是直接在 `GPTSoVits` Conda 环境里执行
- 转换默认输出为：
  - `48kHz`
  - `单声道`
  - `Ogg Vorbis`

## 输出

命令会返回：

- `game_ready_voice_path`
- `override_root`
- `patch_archive_staging_dir`
- `patch_pack_script_path`

并在 `<PROJECT_ROOT>\poc\gptsovits-<target_stem>` 下生成：

- `game-ready/unencrypted/<TARGET_VOICE_FILE>`
- `README.zh-CN.md`

同时会自动刷新：

- `<PROJECT_ROOT>\patch-build\patch2`
- `<PROJECT_ROOT>\patch-build\patch2.manifest.json`
- `<PROJECT_ROOT>\patch-build\pack-patch2.ps1`

## 推荐使用顺序

1. 先跑 `prepare-gptsovits-batch`
2. 跑 `prepare-gptsovits-reinject`
3. 先用 `version.dll + unencrypted` 做快速验证
4. 再决定是否打包成 `patch2.xp3`
