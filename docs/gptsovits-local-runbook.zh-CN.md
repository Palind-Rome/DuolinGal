# GPT-SoVITS 本地复现记录

这份文档记录的是 DuolinGal 在本地机器上，围绕《千恋万花》全年龄语音数据完成一次 **GPT-SoVITS 英文试合成** 的最小复现流程。

目标不是训练整作模型，而是先稳定跑通：

1. `DuolinGal` 生成角色批次
2. `GPT-SoVITS api_v2.py` 启动
3. 丛雨前 10 句英文试合成成功

文档只使用占位符路径，不记录真实用户名、游戏目录或工具目录。

## 前提

- 已经完成全年龄资源提取、脚本反编译、`lines.csv` 构建
- 已经完成角色数据导出：
  - `python -m duolingal export-dataset "<PROJECT_ROOT>" "<VOICE_DIR>"`
- 已经完成 GPT-SoVITS 训练清单准备：
  - `python -m duolingal prepare-gptsovits "<PROJECT_ROOT>"`
- 已经准备好本地 `GPT-SoVITS` 仓库副本

## 一次验证成功的流程

### 1. 创建并进入 Conda 环境

```powershell
conda create -n GPTSoVits python=3.10
conda activate GPTSoVits
```

建议同时屏蔽用户目录里的 Python 包，减少环境干扰：

```powershell
$env:PYTHONNOUSERSITE='1'
```

### 2. 安装 GPT-SoVITS 依赖

在我们这次验证环境中，Windows + CUDA 12.8 的实际可用路线是：

```powershell
cd "<GPT_SOVITS_ROOT>"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Device CU128 -Source HF-Mirror
```

如果 `install.ps1` 在 `torchcodec` 这一步失败，可以改走已验证的手动补装路径：

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r extra-req.txt --no-deps
pip install -r requirements.txt
```

验证 GPU 可用：

```powershell
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

期望输出是：

- `2.11.0+cu128`
- `True`

### 3. 补齐英文推理时缺失的 NLTK 数据

首次跑英文推理时，`g2p_en` 可能会触发 `nltk` 下载运行时数据。我们这次验证中，实际缺的是：

- `averaged_perceptron_tagger_eng`

手动补齐命令：

```powershell
python -m nltk.downloader averaged_perceptron_tagger_eng
```

### 4. 让 GPT-SoVITS 在当前 Windows 环境下绕开 TorchCodec 参考音频读取

在这次实际验证中，`api_v2.py` 服务端能启动，但推理时会因为 `torchaudio.load()` 走到 `TorchCodec` 而失败。

本地可行修复是修改：

- `GPT_SoVITS/TTS_infer_pack/TTS.py`

把 `_get_ref_spec()` 里的：

```python
raw_audio, raw_sr = torchaudio.load(ref_audio_path)
raw_audio = raw_audio.to(self.configs.device).float()
```

替换成：

```python
raw_audio_np, raw_sr = librosa.load(ref_audio_path, sr=None, mono=False)
raw_audio_np = np.asarray(raw_audio_np)
if raw_audio_np.ndim == 1:
    raw_audio_np = np.expand_dims(raw_audio_np, axis=0)
raw_audio = torch.from_numpy(raw_audio_np).to(self.configs.device).float()
```

这个改动是本地工具目录补丁，不属于 DuolinGal 仓库本身。

### 5. 启动 GPT-SoVITS API

```powershell
cd "<GPT_SOVITS_ROOT>"
$env:PYTHONNOUSERSITE='1'
conda activate GPTSoVits
python .\api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

启动成功后会看到类似：

- `device : cuda`
- `version : v2`
- `Uvicorn running on http://127.0.0.1:9880`

### 6. 生成丛雨前 10 句英文试合成批次

```powershell
cd "<REPO_ROOT>"
$env:PYTHONNOUSERSITE='1'
$env:PYTHONPATH='src'
conda activate GPTSoVits
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "ムラサメ" --limit 10
```

输出目录会在：

- `<PROJECT_ROOT>\tts-dataset\ムラサメ\gptsovits\batches\first-10-en`

批次中应包含：

- `requests.jsonl`
- `requests.csv`
- `invoke_api_v2.ps1`
- `outputs\`

### 7. 发起第一批英文试合成

保持 `api_v2.py` 继续运行，在第二个终端执行：

```powershell
cd "<PROJECT_ROOT>\tts-dataset\ムラサメ\gptsovits\batches\first-10-en"
conda activate GPTSoVits
powershell -NoProfile -ExecutionPolicy Bypass -File .\invoke_api_v2.ps1
```

在 DuolinGal 这边，我们额外验证过生成脚本应使用：

```powershell
Get-Content $requestList -Encoding UTF8 | ForEach-Object { ... }
```

否则 Windows PowerShell 5 可能把 UTF-8 的日文 JSONL 按本地编码读坏。

### 8. 成功标志

命令行会依次打印：

- `Generated mur001_001.wav`
- ...
- `Generated mur001_010.wav`

生成结果位于：

- `<PROJECT_ROOT>\tts-dataset\ムラサメ\gptsovits\batches\first-10-en\outputs`

## 这一步为什么“像英文，但不像丛雨”

这是预期现象。

当前这一步是：

- 使用官方预训练权重
- 用单条参考音频做英文试合成

但还没有做：

- 丛雨专属训练
- 丛雨专属微调

所以它能说明：

- 英文推理链路是通的
- 本地 API 可用
- 批量合成请求可跑通

但还不能说明：

- 已经得到稳定的丛雨音色

## 下一步建议

1. 先抽查前 10 句英文输出，挑 1 到 2 句最像样的样本
2. 把它们转成游戏可替换的 `.ogg`
3. 走我们已经验证过的：
   - `version.dll + unencrypted`
   - 或 `patch2.xp3`
4. 做第一轮“GPT-SoVITS 生成音频回灌游戏”验证
5. 只有这一步确认有效后，再决定是否做角色训练/微调
