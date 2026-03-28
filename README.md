# DuolinGal

DuolinGal is a local-first research toolchain for experimenting with English voice workflows in galgames. The current goal is narrow on purpose: prove the extraction, decompile, and line-building pipeline on KiriKiri Z titles such as Senren Banka before touching TTS, patching, or UI polish.

## Current Scope

- Analyze a game directory and identify known KiriKiri Z signatures.
- Initialize a reproducible workspace.
- Prepare a KrkrDump runtime dump config for script assets.
- Optionally run an offline XP3 extraction flow when a compatible CLI exists.
- Decompile SCN or PSB assets into JSON with FreeMote.
- Build `dataset/lines.csv` and `dataset/script_nodes.jsonl`.
- Prepare an all-ages single-line voice replacement PoC workspace.
- Prepare a `patch2.xp3` staging directory from a validated override tree.
- Export per-speaker TTS training datasets from aligned lines and extracted voice files.
- Prepare GPT-SoVITS training lists and English preview mappings from exported speaker datasets.
- Prepare small GPT-SoVITS English synthesis batches for a chosen speaker.
- Prepare a speaker-specific GPT-SoVITS training workspace that calls the official dataset and training scripts.
- Prepare and run a resumable multi-speaker GPT-SoVITS production queue for overnight training, inference, and reinjection staging.

## Privacy Notes

- Keep real game paths, tool paths, and usernames in `configs/toolchain.local.json` only.
- `configs/toolchain.local.json`, `.env`, `.venv/`, and `workspace/projects/` are ignored by Git.
- Documentation uses placeholders such as `<GAME_DIR>` and `<PROJECT_ROOT>` on purpose.

## Quick Start

1. Install the project:

```powershell
pip install -e .
```

2. Copy [configs/toolchain.example.json](configs/toolchain.example.json) to `configs/toolchain.local.json` and edit only the local copy.

3. Run the minimum pipeline:

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "<GAME_DIR>"
python -m duolingal init-project "<GAME_DIR>" --project-id senren-banka
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal prepare-krkrdump "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal decompile-scripts "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal build-lines "<PROJECT_ROOT>"
python -m duolingal prepare-poc "<PROJECT_ROOT>" "<VOICE_DIR>"
python -m duolingal prepare-patch "<PROJECT_ROOT>" "<OVERRIDE_DIR>"
python -m duolingal export-dataset "<PROJECT_ROOT>" "<VOICE_DIR>"
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>"
python -m duolingal prepare-gptsovits-batch "<PROJECT_ROOT>" --speaker "<SPEAKER_NAME>" --limit 10 --reference-mode auto
python -m duolingal prepare-gptsovits-reinject "<PROJECT_ROOT>" "<BATCH_DIR>" --target-voice-file "<TARGET_VOICE_FILE>" --source-output-name "<OUTPUT_WAV_NAME>"
python -m duolingal prepare-gptsovits-reinject-batch "<PROJECT_ROOT>" "<BATCH_DIR>" --limit 50
python -m duolingal prepare-gptsovits-train "<PROJECT_ROOT>" --speaker "<SPEAKER_NAME>"
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" --sync-game-root
python -m duolingal run-gptsovits-production "<PROJECT_ROOT>\\tts-production\\all-cast-v1"
```

## GPT-SoVITS Production Flow

当前仓库已经支持一条可恢复的多角色量产队列，流程是：

```text
export-dataset
  -> prepare-gptsovits
  -> prepare-gptsovits-production
  -> run-gptsovits-production
  -> speaker prepare
  -> speaker GPT
  -> speaker SoVITS
  -> batch infer
  -> wav -> ogg
  -> combined override tree
  -> patch-build
  -> optional game-root sync
```

更具体地说：

- `prepare-gptsovits-production`
  负责扫描角色、生成每个角色的训练工作区、写出夜跑计划和 `run-production.ps1`。
- `run-gptsovits-production`
  负责按计划顺序执行：
  `前处理 -> GPT -> SoVITS -> 切权重 -> 批量推理 -> 转 OGG -> 合并覆盖树 -> 重建 patch-build`
- 队列是可恢复的：
  中断后重新运行同一个 `run-production.ps1`，已完成角色会跳过。
- 队列对坏样本有基础容错：
  英文如果退化成纯标点会尽量在批次准备阶段跳过；个别仍被 `/tts` 判为无效文本的行会被记录并跳过，不再整队中断。
- 队列运行时会持续更新：
  - `production-state.json`
  - `production-status.txt`
- `production-status.txt` 在训练和推理阶段会尽量写出：
  当前 `epoch/batch` 或已完成句数、阶段百分比、已用时、预计剩余时间。

If your environment still uses an offline extractor instead of KrkrDump, `preflight` may recommend `extract` before `decompile-scripts`.

4. Run tests:

```powershell
python -m unittest discover -s tests
```

## Toolchain

- `KrkrDump`
  Preferred for KiriKiri Z script extraction. DuolinGal prepares `KrkrDump.json` and prints the launch command; the actual dump still runs on your local machine.
- `FreeMote`
  Used to decompile `.scn`, `.psb`, and `.psb.m` into JSON.
- `KrkrExtract`
  Kept as an optional offline fallback when a compatible CLI workflow is available.
- `FFmpeg`
  Planned for audio preprocessing.
- `GPT-SoVITS`
  Supported for training list preparation, speaker-specific training workspace generation, and resumable multi-speaker production queues; actual model installation remains external, and generated GPT / SoVITS training workspaces use Windows-safe single-GPU launchers.

## Local API

Install optional API dependencies and start FastAPI:

```powershell
pip install -e .[api]
$env:PYTHONPATH='src'
uvicorn duolingal.api.app:create_app --factory --reload
```

Available routes:

- `GET /health`
- `GET /api/tools`
- `POST /api/analyze`
- `POST /api/projects/init`
- `POST /api/projects/extract`
- `POST /api/projects/decompile-scripts`
- `POST /api/projects/prepare-krkrdump`
- `POST /api/projects/preflight`
- `POST /api/projects/build-lines`
- `POST /api/projects/prepare-poc`
- `POST /api/projects/prepare-patch`
- `POST /api/projects/export-dataset`
- `POST /api/projects/prepare-gptsovits`
- `POST /api/projects/prepare-gptsovits-batch`
- `POST /api/projects/prepare-gptsovits-reinject`
- `POST /api/projects/prepare-gptsovits-reinject-batch`
- `POST /api/projects/prepare-gptsovits-train`
- `POST /api/projects/prepare-gptsovits-production`
- `POST /api/projects/run-gptsovits-production`

## Repository Layout

```text
DuolinGal/
|-- apps/
|-- configs/
|-- docs/
|-- src/duolingal/
|   |-- api/
|   |-- core/
|   |-- domain/
|   `-- services/
`-- tests/
```

## Documents

- [Feasibility and Risk Assessment](docs/feasibility.zh-CN.md)
- [Project Plan](docs/project-plan.zh-CN.md)
- [Structure and Runtime Flow](docs/structure-and-runtime.zh-CN.md)
- [Path and Directory Assumptions](docs/path-assumptions.zh-CN.md)
- [Local Validation Checklist](docs/local-validation-checklist.zh-CN.md)
- [Single-line PoC Guide](docs/single-line-poc.zh-CN.md)
- [Patch Packaging Guide](docs/patch-packaging.zh-CN.md)
- [Dataset Export Guide](docs/dataset-export.zh-CN.md)
- [GPT-SoVITS Preparation Guide](docs/gptsovits-prep.zh-CN.md)
- [GPT-SoVITS Batch Guide](docs/gptsovits-batch.zh-CN.md)
- [GPT-SoVITS Reinject Guide](docs/gptsovits-reinject.zh-CN.md)
- [GPT-SoVITS Training Guide](docs/gptsovits-training.zh-CN.md)
- [GPT-SoVITS Local Runbook](docs/gptsovits-local-runbook.zh-CN.md)
- [GPT-SoVITS Production Guide](docs/gptsovits-production.zh-CN.md)

## Boundaries

- The repository does not ship commercial game assets.
- The repository currently targets a research workflow, not a turnkey English dub patcher.
- External binaries such as KrkrDump, FreeMote, KrkrExtract, and KirikiriTools should remain external dependencies.
