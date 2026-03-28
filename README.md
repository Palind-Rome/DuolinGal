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
```

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
  Planned for voice cloning and synthesis.

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
- [Local Validation Checklist](docs/local-validation-checklist.zh-CN.md)
- [Single-line PoC Guide](docs/single-line-poc.zh-CN.md)
- [Patch Packaging Guide](docs/patch-packaging.zh-CN.md)
- [Dataset Export Guide](docs/dataset-export.zh-CN.md)

## Boundaries

- The repository does not ship commercial game assets.
- The repository currently targets a research workflow, not a turnkey English dub patcher.
- External binaries such as KrkrDump, FreeMote, KrkrExtract, and KirikiriTools should remain external dependencies.
