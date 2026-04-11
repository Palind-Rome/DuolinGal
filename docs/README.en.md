<div align="center">
<img src="../image/Logo.png" alt="DuolinGal" width="400" /> 

**DuolinGal: A cross-language voice conversion workflow for KiriKiri Z galgames**

Play galgames with English or Chinese voice acting.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/Palind-Rome/DuolinGal?style=social)](https://github.com/Palind-Rome/DuolinGal)

[Chinese README](../README.md) · [Quick Start](#quick-start) · [Workflow Paths](#choose-a-path-by-goal) · [Documentation Map](#documentation-map) · [Local API](#local-api) · [Repository Layout](#repository-layout)

</div>

---

# TL;DR

DuolinGal is a local-first tooling workflow for KiriKiri Z galgames. It is meant to help you build English or Chinese voice-over versions of a game.

This workflow has already been validated end-to-end on *Senren＊Banka*, covering resource extraction, line alignment, speaker dataset export, GPT-SoVITS training, batch inference, and reinjection back into the game.

The English voice patch produced with this workflow for *Senren＊Banka* has already been published on [GitHub Releases](https://github.com/Palind-Rome/DuolinGal/releases). Download it, place it in the game directory, and play.

The following upstream tools were central to this workflow. If you find this project useful, please consider starring or supporting their original projects:

- [GARbro](https://github.com/morkt/GARbro)
  Used mainly for early-stage offline unpacking and manual asset exploration.
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
  Handles character voice cloning, speaker training, and speaker inference. It is the core of the voice generation pipeline.
- [FreeMote](https://github.com/UlyssesWu/FreeMote)
  Used to decompile and rebuild `.scn`, `.psb`, and `.psb.m` assets commonly seen in KiriKiri games.
- [KirikiriTools](https://github.com/arcusmaximus/KirikiriTools)
  Used for `patch2.xp3` packaging; the in-game `version.dll` override path also comes from this project.
- [FFmpeg](https://ffmpeg.org/)
  Used for trimming, resampling, format conversion, and `wav -> ogg` transcoding.
- [KrkrDump](https://github.com/crskycode/KrkrDump)
  The repository includes commands for it and we attempted to use it locally, but it was not part of the final extraction path that successfully reproduced this *Senren＊Banka* workflow.
- [KrkrExtract](https://github.com/xmoezzz/KrkrExtract)
  Optional; can be used for offline XP3 unpacking or repacking.

> Note: For the successful English dubbing workflow on *Senren＊Banka*, the unpacking path I actually reproduced used `GARbro`. The codebase still keeps `KrkrDump` and `KrkrExtract` entry points, but I have not reproduced the full workflow with them.

# DuolinGal

DuolinGal is a local-first tooling workflow for KiriKiri Z galgames.  
It turns:

`resource extraction -> line alignment -> speaker dataset export -> GPT-SoVITS training/production -> game patch reinjection`

into a reproducible engineering workflow suitable for:

- English dubbing patches
- Chinese dubbing patches
- speaker-level TTS research and batch validation

The current project has already been proven on *Senren＊Banka* with:

- resource extraction and script decompilation
- line and voice alignment
- speaker dataset export
- GPT-SoVITS single-speaker training
- resumable overnight multi-speaker production
- batch `wav -> ogg` reinjection
- in-game `unencrypted/` override testing and `patch-build` reconstruction
- final `.xp3` patch packaging and release

## Project Goals

DuolinGal is not trying to be a one-click commercial patching product. It is an engineered workflow that solves these problems:

1. Turn galgame text, voices, and speakers into trainable datasets
2. Run GPT-SoVITS training and batch inference reliably on Windows with a single GPU
3. Reorganize synthesized outputs into a tree the game can directly override
4. Package the result into a releasable English voice patch

## Current Capabilities

- Analyze a game directory and detect common KiriKiri Z traits
- Initialize a reproducible project workspace
- Support manual unpacking as the currently validated extraction path
- Call external tools to decompile `.scn` / `.psb`
- Build `lines.csv` and script node indexes
- Export speaker-level TTS datasets
- Prepare GPT-SoVITS training lists and English previews
- Generate single-speaker GPT-SoVITS training workspaces
- Generate and run resumable multi-speaker GPT-SoVITS production queues
- Convert synthesized outputs into game-ready `.ogg`
- Rebuild project-level `patch-build`
- Package final `.xp3` patches

## Quick Start

### 0. Prepare External Dependencies

Before you begin, make sure the following are available:

- `GARbro`
  The currently validated main path is manual extraction of `scn.xp3` and `voice.xp3`
- `FreeMote`
  Used to decompile script assets
- `FFmpeg`
  Used for audio format conversion
- `KirikiriTools`
  Used for final `patch2.xp3` packaging
- A local `GPT-SoVITS` repository
- A `GPTSoVits` conda environment

> The successfully reproduced path right now is: **manual unpacking + DuolinGal project building + local GPT-SoVITS training/production**.  
> `prepare-krkrdump` and `KrkrExtract` related entry points are still present, but were not part of the reproduced mainline workflow.

### 1. Install the Repository

```powershell
pip install -e .
```

### 2. Prepare Local Configuration

Copy:

- [../configs/toolchain.example.json](../configs/toolchain.example.json)

to:

- `configs/toolchain.local.json`

Then edit only your local copy.

Because automatic unpacking was not successfully reproduced in the validated path, you can leave unpacking tool paths such as `krkrdump` and `krkrextract` empty and simply unpack the game resources manually into the expected directories.

### 3. Initialize a Project and Export Speaker Data

```powershell
$env:PYTHONPATH='src'
python -m duolingal analyze "<GAME_DIR>"
python -m duolingal init-project "<GAME_DIR>" --project-id senren-banka

# Since automatic unpacking was not reproduced successfully,
# use GARbro or another unpacking tool here instead:
# 1. extract scn.xp3   into "<PROJECT_ROOT>\extracted_script"
# 2. extract voice.xp3 into "<PROJECT_ROOT>\extracted_voice"

python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal decompile-scripts "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal preflight "<PROJECT_ROOT>" --config configs/toolchain.local.json
python -m duolingal build-lines "<PROJECT_ROOT>"
python -m duolingal export-dataset "<PROJECT_ROOT>" "<PROJECT_ROOT>\extracted_voice"
python -m duolingal prepare-gptsovits "<PROJECT_ROOT>"
```

At this point you have finished:

- project initialization
- script and voice export
- speaker-level training list generation
- English preview generation

From here, choose one of the workflow paths below depending on your goal.

## Choose a Path by Goal

### A. Single-Speaker Validation

If you want to verify whether one character can be trained successfully and whether the result sounds like the original character, the recommended sequence is:

```text
prepare-gptsovits-train
  -> run-prepare-all.ps1
  -> run-train-gpt.ps1
  -> run-train-sovits.ps1
  -> prepare English batch
  -> local listening / reinjection into the game
```

First generate a single-speaker training workspace:

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-train "<PROJECT_ROOT>" --speaker "<SPEAKER_NAME>"
```

Notes:

- If `configs/toolchain.local.json` already has `gpt-sovits.path` pointing at your local `api_v2.py`, this command now resolves the matching GPT-SoVITS repository root automatically.
- Pass `--config "<CONFIG_PATH>"` if you want to use a non-default toolchain config file.
- `--gpt-sovits-root "<GPT_SOVITS_DIR>"` is still supported and overrides the config entry.

Then go to the generated:

- `tts-training/<EXPERIMENT_NAME>/scripts/`

and run, in order:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-prepare-all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-train-gpt.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-train-sovits.ps1
```

Helpful references:

- [GPT-SoVITS Training Guide](gptsovits-training.zh-CN.md)
- [GPT-SoVITS Local Runbook](gptsovits-local-runbook.zh-CN.md)
- [GPT-SoVITS Batch Guide](gptsovits-batch.zh-CN.md)
- [GPT-SoVITS Reinject Guide](gptsovits-reinject.zh-CN.md)

### B. Multi-Speaker Production

If you are no longer validating one speaker and instead want to train multiple speakers in sequence and generate English voice lines at scale, the recommended path is:

```text
prepare-gptsovits-production
  -> run-gptsovits-production
  -> for each speaker automatically:
     prepare -> GPT -> SoVITS -> switch weights -> infer -> wav -> ogg
  -> merge combined override tree
  -> rebuild patch-build
  -> optionally sync into the real game directory
```

First prepare a production plan:

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" --sync-game-root
```

If you only want a subset of speakers:

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-gptsovits-production "<PROJECT_ROOT>" `
  --speaker "ムラサメ" `
  --speaker "芳乃" `
  --speaker "茉子"
```

Then run:

```powershell
$env:PYTHONPATH='src'
python -m duolingal run-gptsovits-production "<PROJECT_ROOT>\tts-production\all-cast-v1"
```

Or directly execute the generated:

- `tts-production/<PLAN_NAME>/scripts/run-production.ps1`

If some speakers need fixed anchor prompts, or if some speakers should be excluded from production, place:

- `tts-production/production-overrides.json`

in the project root.

For the detailed production workflow, see:

- [GPT-SoVITS Production Guide](gptsovits-production.zh-CN.md)

### C. Final Cleanup and Release

After production finishes, do **not** delete from the original outputs directly. The correct order is:

```text
run-gptsovits-production
  -> prepare-final-cleanup
  -> review cleanup-review.ready.csv
  -> delete .ogg files that should fall back to JP from the copy
  -> rebuild-patch-from-clean-copy.ps1
  -> patch-build/pack-patch2.ps1
  -> patch2.xp3
```

First generate a safe copy:

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-final-cleanup "<PROJECT_ROOT>"
```

Then in:

- `tts-release/final-cleanup-v1/review/cleanup-review.ready.csv`

mark only the rows that should fall back to the original Japanese voice as `remove`.  
Then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<PROJECT_ROOT>\tts-release\final-cleanup-v1\scripts\apply-reviewed-removals.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "<PROJECT_ROOT>\tts-release\final-cleanup-v1\scripts\rebuild-patch-from-clean-copy.ps1"
```

Finally go to:

- `<PROJECT_ROOT>\patch-build`

and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\pack-patch2.ps1
```

This produces:

- `<PROJECT_ROOT>\patch-build\patch2.xp3`

## What the GPT-SoVITS Production Queue Actually Does

The repository already supports a **resumable** multi-speaker production queue:

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

More concretely:

- `prepare-gptsovits-production`
  scans speakers, generates training workspaces, and writes the overnight plan plus `run-production.ps1`
- `run-gptsovits-production`
  executes:
  `prepare -> GPT -> SoVITS -> switch weights -> batch inference -> OGG conversion -> merge override tree -> rebuild patch-build`
- The queue is resumable
  re-running the same `run-production.ps1` skips speakers that are already finished
- The queue continuously updates:
  - `production-state.json`
  - `production-status.txt`

## Weights and Outputs Must Be Preserved

This is important: **trained character weights, configs, and generated batch outputs should all be kept long-term.**

At minimum, keep:

- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/weights/gpt/`
- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/weights/sovits/`
- `<PROJECT_ROOT>/tts-training/<EXPERIMENT_NAME>/configs/`
- `<PROJECT_ROOT>/tts-production/<PLAN_NAME>/`

Why:

- these weights already cost you time, GPU hours, and tuning effort
- they can be reused not only for English, but also for later versions in other languages

## Policy for Keeping Weak Utterances in the Original Japanese

The repository already has basic protection:

- purely punctuation-only English targets are skipped during batch preparation
- individual lines rejected by `/tts` as invalid text are logged and skipped

But stronger cleanup for weak utterances, interjections, barks, and non-lexical sounds is still recommended as a **final cleanup step after the full production run**, not as an aggressive rule inside the main production pipeline.

Why:

- filtering too early risks deleting English lines that actually came out well
- finishing production first preserves the fullest possible first-pass result
- if you later remove some `.ogg` files, the game naturally falls back to the original Japanese voice

The recommended order remains:

1. Finish the full training / inference / conversion / override-tree build
2. Run `prepare-final-cleanup` to create a safe copy
3. Review `cleanup-review.ready.csv`
4. Clean weak utterances, barks, and non-lexical lines in the copy
5. Rebuild `patch-build` from the cleaned copy
6. Package the cleaned copy for the final release

Command:

```powershell
$env:PYTHONPATH='src'
python -m duolingal prepare-final-cleanup "<PROJECT_ROOT>"
```

## Documentation Map

- [Feasibility and Risk Assessment](feasibility.zh-CN.md)
- [Project Plan](project-plan.zh-CN.md)
- [Structure and Runtime Flow](structure-and-runtime.zh-CN.md)
- [Local Validation Checklist](local-validation-checklist.zh-CN.md)
- [Single-line PoC Guide](single-line-poc.zh-CN.md)
- [Patch Packaging Guide](patch-packaging.zh-CN.md)
- [Dataset Export Guide](dataset-export.zh-CN.md)
- [GPT-SoVITS Preparation Guide](gptsovits-prep.zh-CN.md)
- [GPT-SoVITS Batch Guide](gptsovits-batch.zh-CN.md)
- [GPT-SoVITS Reinject Guide](gptsovits-reinject.zh-CN.md)
- [GPT-SoVITS Training Guide](gptsovits-training.zh-CN.md)
- [GPT-SoVITS Local Runbook](gptsovits-local-runbook.zh-CN.md)
- [GPT-SoVITS Production Guide](gptsovits-production.zh-CN.md)

## Local API

If you are only reproducing the CLI workflow above, you can safely skip this section at first.  
The local API is more useful if you later want to wrap the pipeline with your own UI or service layer.

Optionally install API dependencies and start FastAPI:

```powershell
pip install -e .[api]
$env:PYTHONPATH='src'
uvicorn duolingal.api.app:create_app --factory --reload
```

Available endpoints:

- `GET /health`
- `POST /api/analyze`
- `POST /api/projects/init`
- `POST /api/projects/preflight`
- `POST /api/projects/build-lines`
- `POST /api/projects/export-dataset`
- `POST /api/projects/prepare-gptsovits`
- `POST /api/projects/prepare-gptsovits-batch`
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

## Current Boundaries

What the repository has already proven:

- speaker-level training can run reliably on Windows with a single GPU
- multi-speaker production can keep moving forward at scale
- final weak-utterance cleanup can be done safely on a copy while preserving JP fallback
- generated audio can genuinely be reinjected back into the game for real playtesting

What it still does **not** solve:

- a proper pronunciation dictionary for proper nouns, so names are not always read with default English pronunciation
- automatic best-epoch search
- fully automatic final classification of weak utterances and barks; human review is still recommended

So at the current stage, DuolinGal is best understood as:

- an already working **engineering-oriented research workflow**
- a **local production entry point** that can keep producing real results

## License

[MIT License](../LICENSE)
