from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import GptSovitsTrainingPreparationResult


def prepare_gptsovits_training(
    project_root: str | Path,
    speaker_name: str,
    *,
    gpt_sovits_root: str | Path | None = None,
    version: str = "v2",
    gpu: str = "0",
    is_half: bool = True,
    gpt_epochs: int = 12,
    sovits_epochs: int = 20,
    gpt_batch_size: int = 4,
    sovits_batch_size: int = 4,
) -> GptSovitsTrainingPreparationResult:
    if version != "v2":
        raise ValueError("Only GPT-SoVITS v2 training preparation is supported right now.")
    if gpt_epochs < 1 or sovits_epochs < 1:
        raise ValueError("Epoch counts must be at least 1.")
    if gpt_batch_size < 1 or sovits_batch_size < 1:
        raise ValueError("Batch sizes must be at least 1.")

    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    speaker_dir, rows, current_speaker_name = _find_speaker_dataset(resolved_project_root / "tts-dataset", speaker_name)

    resolved_gpt_root = _resolve_gpt_sovits_root(resolved_project_root, gpt_sovits_root)
    _validate_gpt_sovits_root(resolved_gpt_root)

    prepared_rows = _collect_training_rows(speaker_dir, rows)
    if not prepared_rows:
        raise ValueError(f"No training rows with audio and Japanese text were found for speaker: {speaker_name}")

    experiment_name = _derive_experiment_name(current_speaker_name, prepared_rows)
    speaker_alias = experiment_name.replace("-", "_")

    training_root = resolved_project_root / "tts-training" / experiment_name
    inputs_dir = training_root / "inputs"
    configs_dir = training_root / "configs"
    scripts_dir = training_root / "scripts"
    exp_dir = training_root / "exp" / experiment_name
    weights_dir = training_root / "weights"
    gpt_weights_dir = weights_dir / "gpt"
    sovits_weights_dir = weights_dir / "sovits"

    inputs_dir.mkdir(parents=True, exist_ok=True)
    configs_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)
    gpt_weights_dir.mkdir(parents=True, exist_ok=True)
    sovits_weights_dir.mkdir(parents=True, exist_ok=True)

    input_list_path = inputs_dir / "train_ja.list"
    _write_training_input_list(input_list_path, prepared_rows, speaker_alias)
    staged_audio_root = training_root / "source-audio"
    _materialize_ascii_source_audio(staged_audio_root, prepared_rows)

    gpt_config_path = configs_dir / "s1-v2.yaml"
    sovits_config_path = configs_dir / "s2-v2.json"
    gpt_config_path.write_text(
        _build_gpt_config(
            experiment_name=experiment_name,
            exp_dir=exp_dir,
            gpt_weights_dir=gpt_weights_dir,
            pretrained_s1=resolved_gpt_root / "GPT_SoVITS" / "pretrained_models" / "gsv-v2final-pretrained" / "s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
            gpt_epochs=gpt_epochs,
            gpt_batch_size=gpt_batch_size,
        ),
        encoding="utf-8",
        newline="\n",
    )
    sovits_config_path.write_text(
        _build_sovits_config(
            resolved_gpt_root=resolved_gpt_root,
            experiment_name=experiment_name,
            exp_dir=exp_dir,
            sovits_weights_dir=sovits_weights_dir,
            sovits_epochs=sovits_epochs,
            sovits_batch_size=sovits_batch_size,
            gpu=gpu,
            is_half=is_half,
            version=version,
        ),
        encoding="utf-8",
        newline="\n",
    )

    prepare_stage1_script_path = scripts_dir / "run-prepare-stage1.ps1"
    prepare_stage2_script_path = scripts_dir / "run-prepare-stage2.ps1"
    prepare_stage3_script_path = scripts_dir / "run-prepare-stage3.ps1"
    prepare_all_script_path = scripts_dir / "run-prepare-all.ps1"
    train_gpt_script_path = scripts_dir / "run-train-gpt.ps1"
    train_sovits_script_path = scripts_dir / "run-train-sovits.ps1"
    train_all_script_path = scripts_dir / "run-train-all.ps1"
    readme_path = training_root / "README.zh-CN.md"

    common_paths = _CommonPaths(
        gpt_sovits_root=resolved_gpt_root,
        input_list_path=input_list_path,
        source_audio_root=staged_audio_root,
        exp_dir=exp_dir,
        gpu=gpu,
        is_half=is_half,
    )

    prepare_stage1_script_path.write_text(
        _build_prepare_stage1_script(common_paths, version=version),
        encoding="utf-8",
        newline="\n",
    )
    prepare_stage2_script_path.write_text(
        _build_prepare_stage2_script(common_paths),
        encoding="utf-8",
        newline="\n",
    )
    prepare_stage3_script_path.write_text(
        _build_prepare_stage3_script(common_paths, sovits_config_path=sovits_config_path),
        encoding="utf-8",
        newline="\n",
    )
    prepare_all_script_path.write_text(
        _build_prepare_all_script(),
        encoding="utf-8",
        newline="\n",
    )
    train_gpt_script_path.write_text(
        _build_train_gpt_script(
            gpt_sovits_root=resolved_gpt_root,
            gpt_config_path=gpt_config_path,
            gpu=gpu,
        ),
        encoding="utf-8",
        newline="\n",
    )
    train_sovits_script_path.write_text(
        _build_train_sovits_script(
            gpt_sovits_root=resolved_gpt_root,
            sovits_config_path=sovits_config_path,
            gpu=gpu,
        ),
        encoding="utf-8",
        newline="\n",
    )
    train_all_script_path.write_text(
        _build_train_all_script(),
        encoding="utf-8",
        newline="\n",
    )
    readme_path.write_text(
        _build_readme(
            speaker_name=current_speaker_name,
            speaker_alias=speaker_alias,
            experiment_name=experiment_name,
            line_count=len(prepared_rows),
        ),
        encoding="utf-8",
        newline="\n",
    )

    return GptSovitsTrainingPreparationResult(
        project_root=str(resolved_project_root),
        speaker_name=current_speaker_name,
        speaker_alias=speaker_alias,
        experiment_name=experiment_name,
        gpt_sovits_root=str(resolved_gpt_root),
        training_root=str(training_root),
        source_audio_root=str(staged_audio_root.resolve()),
        input_list_path=str(input_list_path),
        exp_dir=str(exp_dir),
        gpt_config_path=str(gpt_config_path),
        sovits_config_path=str(sovits_config_path),
        prepare_stage1_script_path=str(prepare_stage1_script_path),
        prepare_stage2_script_path=str(prepare_stage2_script_path),
        prepare_stage3_script_path=str(prepare_stage3_script_path),
        prepare_all_script_path=str(prepare_all_script_path),
        train_gpt_script_path=str(train_gpt_script_path),
        train_sovits_script_path=str(train_sovits_script_path),
        train_all_script_path=str(train_all_script_path),
        readme_path=str(readme_path),
        line_count=len(prepared_rows),
        notes=[
            "This preparation keeps the original galgame OGG files as the source dataset and does not normalize or trim them.",
            "The generated experiment directory is ASCII-friendly so official GPT-SoVITS scripts are less likely to trip on Windows path encoding.",
            "Run dataset preparation first, then GPT training, then SoVITS training in the activated GPTSoVits conda environment.",
        ],
    )


class _CommonPaths:
    def __init__(
        self,
        *,
        gpt_sovits_root: Path,
        input_list_path: Path,
        source_audio_root: Path,
        exp_dir: Path,
        gpu: str,
        is_half: bool,
    ) -> None:
        self.gpt_sovits_root = gpt_sovits_root
        self.input_list_path = input_list_path
        self.source_audio_root = source_audio_root
        self.exp_dir = exp_dir
        self.gpu = gpu
        self.is_half = is_half


def _find_speaker_dataset(dataset_root: Path, speaker_name: str) -> tuple[Path, list[dict[str, str]], str]:
    if not dataset_root.exists():
        raise ValueError(f"TTS dataset root does not exist: {dataset_root}")

    normalized_target = speaker_name.casefold()
    for speaker_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        metadata_path = speaker_dir / "metadata.csv"
        if not metadata_path.exists():
            continue

        with metadata_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue

        current_speaker_name = (rows[0].get("speaker_name") or speaker_dir.name).strip() or speaker_dir.name
        if current_speaker_name.casefold() == normalized_target:
            return speaker_dir, rows, current_speaker_name

    raise ValueError(f"Speaker dataset was not found: {speaker_name}")


def _resolve_gpt_sovits_root(project_root: Path, gpt_sovits_root: str | Path | None) -> Path:
    if gpt_sovits_root is not None:
        return Path(gpt_sovits_root).expanduser().resolve()

    repo_root = project_root.parents[2]
    return (repo_root.parent / "tools" / "GPT-SoVITS").resolve()


def _validate_gpt_sovits_root(gpt_sovits_root: Path) -> None:
    required_paths = [
        gpt_sovits_root / "GPT_SoVITS" / "prepare_datasets" / "1-get-text.py",
        gpt_sovits_root / "GPT_SoVITS" / "prepare_datasets" / "2-get-hubert-wav32k.py",
        gpt_sovits_root / "GPT_SoVITS" / "prepare_datasets" / "3-get-semantic.py",
        gpt_sovits_root / "GPT_SoVITS" / "s1_train.py",
        gpt_sovits_root / "GPT_SoVITS" / "s2_train.py",
        gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "gsv-v2final-pretrained" / "s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
        gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "gsv-v2final-pretrained" / "s2G2333k.pth",
        gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "gsv-v2final-pretrained" / "s2D2333k.pth",
        gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large",
        gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base",
    ]
    for required_path in required_paths:
        if not required_path.exists():
            raise ValueError(f"GPT-SoVITS prerequisite path does not exist: {required_path}")


def _collect_training_rows(speaker_dir: Path, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    prepared_rows: list[dict[str, str]] = []
    for row in rows:
        voice_file = (row.get("voice_file") or "").strip()
        jp_text = (row.get("jp_text") or "").strip()
        if not voice_file or not jp_text:
            continue

        audio_path = speaker_dir / (row.get("audio_path") or "")
        if not audio_path.exists():
            continue

        prepared_rows.append(
            {
                "voice_file": voice_file,
                "jp_text": jp_text,
                "audio_path": str(audio_path.resolve()),
            }
        )
    return prepared_rows


def _materialize_ascii_source_audio(staged_audio_root: Path, rows: list[dict[str, str]]) -> None:
    staged_audio_root.mkdir(parents=True, exist_ok=True)
    for row in rows:
        source_path = Path(row["audio_path"])
        destination_path = staged_audio_root / row["voice_file"]
        if destination_path.exists():
            continue

        try:
            destination_path.hardlink_to(source_path)
        except OSError:
            shutil.copy2(source_path, destination_path)


def _derive_experiment_name(speaker_name: str, rows: list[dict[str, str]]) -> str:
    prefix = ""
    if rows:
        match = re.match(r"([A-Za-z]+)", rows[0]["voice_file"])
        if match:
            prefix = match.group(1).lower()

    if not prefix:
        digest = hashlib.sha1(speaker_name.encode("utf-8")).hexdigest()[:8]
        prefix = f"speaker-{digest}"

    return f"{prefix}-v2"


def _write_training_input_list(input_list_path: Path, rows: list[dict[str, str]], speaker_alias: str) -> None:
    with input_list_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(f"{row['voice_file']}|{speaker_alias}|ja|{row['jp_text']}\n")


def _build_gpt_config(
    *,
    experiment_name: str,
    exp_dir: Path,
    gpt_weights_dir: Path,
    pretrained_s1: Path,
    gpt_epochs: int,
    gpt_batch_size: int,
) -> str:
    return (
        "train:\n"
        "  seed: 1234\n"
        f"  epochs: {gpt_epochs}\n"
        f"  batch_size: {gpt_batch_size}\n"
        "  save_every_n_epoch: 1\n"
        "  precision: 16-mixed\n"
        "  gradient_clip: 1.0\n"
        "  if_save_latest: true\n"
        "  if_save_every_weights: true\n"
        f"  half_weights_save_dir: {json.dumps(str(gpt_weights_dir))}\n"
        f"  exp_name: {json.dumps(experiment_name)}\n"
        "optimizer:\n"
        "  lr: 0.01\n"
        "  lr_init: 0.00001\n"
        "  lr_end: 0.0001\n"
        "  warmup_steps: 2000\n"
        "  decay_steps: 40000\n"
        "data:\n"
        "  max_eval_sample: 8\n"
        "  max_sec: 54\n"
        "  num_workers: 4\n"
        "  pad_val: 1024\n"
        "model:\n"
        "  vocab_size: 1025\n"
        "  phoneme_vocab_size: 732\n"
        "  embedding_dim: 512\n"
        "  hidden_dim: 512\n"
        "  head: 16\n"
        "  linear_units: 2048\n"
        "  n_layer: 24\n"
        "  dropout: 0\n"
        "  EOS: 1024\n"
        "  random_bert: 0\n"
        "inference:\n"
        "  top_k: 15\n"
        f"pretrained_s1: {json.dumps(str(pretrained_s1))}\n"
        f"train_semantic_path: {json.dumps(str(exp_dir / '6-name2semantic.tsv'))}\n"
        f"train_phoneme_path: {json.dumps(str(exp_dir / '2-name2text.txt'))}\n"
        f"output_dir: {json.dumps(str(exp_dir / 'logs_s1_v2'))}\n"
    )


def _build_sovits_config(
    *,
    resolved_gpt_root: Path,
    experiment_name: str,
    exp_dir: Path,
    sovits_weights_dir: Path,
    sovits_epochs: int,
    sovits_batch_size: int,
    gpu: str,
    is_half: bool,
    version: str,
) -> str:
    config = {
        "train": {
            "log_interval": 100,
            "eval_interval": 500,
            "seed": 1234,
            "epochs": sovits_epochs,
            "learning_rate": 0.0001,
            "betas": [0.8, 0.99],
            "eps": 1e-09,
            "batch_size": sovits_batch_size,
            "fp16_run": is_half,
            "lr_decay": 0.999875,
            "segment_size": 20480,
            "init_lr_ratio": 1,
            "warmup_epochs": 0,
            "c_mel": 45,
            "c_kl": 1.0,
            "text_low_lr_rate": 0.4,
            "grad_ckpt": False,
            "pretrained_s2G": str(
                resolved_gpt_root
                / "GPT_SoVITS"
                / "pretrained_models"
                / "gsv-v2final-pretrained"
                / "s2G2333k.pth"
            ),
            "pretrained_s2D": str(
                resolved_gpt_root
                / "GPT_SoVITS"
                / "pretrained_models"
                / "gsv-v2final-pretrained"
                / "s2D2333k.pth"
            ),
            "if_save_latest": 1,
            "if_save_every_weights": True,
            "save_every_epoch": 1,
            "gpu_numbers": gpu,
        },
        "data": {
            "max_wav_value": 32768.0,
            "sampling_rate": 32000,
            "filter_length": 2048,
            "hop_length": 640,
            "win_length": 2048,
            "n_mel_channels": 128,
            "mel_fmin": 0.0,
            "mel_fmax": None,
            "add_blank": True,
            "n_speakers": 300,
            "cleaned_text": True,
            "exp_dir": str(exp_dir),
        },
        "model": {
            "inter_channels": 192,
            "hidden_channels": 192,
            "filter_channels": 768,
            "n_heads": 2,
            "n_layers": 6,
            "kernel_size": 3,
            "p_dropout": 0.1,
            "resblock": "1",
            "resblock_kernel_sizes": [3, 7, 11],
            "resblock_dilation_sizes": [[1, 3, 5], [1, 3, 5], [1, 3, 5]],
            "upsample_rates": [10, 8, 2, 2, 2],
            "upsample_initial_channel": 512,
            "upsample_kernel_sizes": [16, 16, 8, 2, 2],
            "n_layers_q": 3,
            "use_spectral_norm": False,
            "gin_channels": 512,
            "semantic_frame_rate": "25hz",
            "freeze_quantizer": True,
            "version": version,
        },
        "s2_ckpt_dir": str(exp_dir),
        "save_weight_dir": str(sovits_weights_dir),
        "name": experiment_name,
        "version": version,
        "content_module": "cnhubert",
    }
    return json.dumps(config, ensure_ascii=False, indent=2)


def _build_prepare_stage1_script(common_paths: _CommonPaths, *, version: str) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = '{common_paths.gpt_sovits_root};{common_paths.gpt_sovits_root / "GPT_SoVITS"}'
$env:inp_text = '{common_paths.input_list_path}'
$env:inp_wav_dir = '{common_paths.source_audio_root}'
$env:exp_name = '{common_paths.exp_dir.name}'
$env:opt_dir = '{common_paths.exp_dir}'
$env:bert_pretrained_dir = '{common_paths.gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large"}'
$env:i_part = '0'
$env:all_parts = '1'
$env:_CUDA_VISIBLE_DEVICES = '{common_paths.gpu}'
$env:is_half = '{str(common_paths.is_half)}'
$env:version = '{version}'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

Set-Location '{common_paths.gpt_sovits_root}'
& $pythonExe -s GPT_SoVITS/prepare_datasets/1-get-text.py

$partial = Join-Path $env:opt_dir '2-name2text-0.txt'
$merged = Join-Path $env:opt_dir '2-name2text.txt'
if (-not (Test-Path $partial -PathType Leaf)) {{
  throw "Stage 1 output not found: $partial"
}}
Move-Item -Force $partial $merged
Write-Host "Prepared $merged"
"""


def _build_prepare_stage2_script(common_paths: _CommonPaths) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = '{common_paths.gpt_sovits_root};{common_paths.gpt_sovits_root / "GPT_SoVITS"}'
$env:inp_text = '{common_paths.input_list_path}'
$env:inp_wav_dir = '{common_paths.source_audio_root}'
$env:exp_name = '{common_paths.exp_dir.name}'
$env:opt_dir = '{common_paths.exp_dir}'
$env:cnhubert_base_dir = '{common_paths.gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base"}'
$env:i_part = '0'
$env:all_parts = '1'
$env:_CUDA_VISIBLE_DEVICES = '{common_paths.gpu}'
$env:is_half = '{str(common_paths.is_half)}'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

Set-Location '{common_paths.gpt_sovits_root}'
& $pythonExe -s GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py

Write-Host "Prepared 4-cnhubert and 5-wav32k under {common_paths.exp_dir}"
"""


def _build_prepare_stage3_script(common_paths: _CommonPaths, *, sovits_config_path: Path) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = '{common_paths.gpt_sovits_root};{common_paths.gpt_sovits_root / "GPT_SoVITS"}'
$env:inp_text = '{common_paths.input_list_path}'
$env:exp_name = '{common_paths.exp_dir.name}'
$env:opt_dir = '{common_paths.exp_dir}'
$env:pretrained_s2G = '{common_paths.gpt_sovits_root / "GPT_SoVITS" / "pretrained_models" / "gsv-v2final-pretrained" / "s2G2333k.pth"}'
$env:s2config_path = '{sovits_config_path}'
$env:i_part = '0'
$env:all_parts = '1'
$env:_CUDA_VISIBLE_DEVICES = '{common_paths.gpu}'
$env:is_half = '{str(common_paths.is_half)}'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

$stage3Config = Join-Path $env:opt_dir 's2config.stage3.json'
$config = Get-Content $env:s2config_path -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.model -and $config.model.PSObject.Properties.Name -contains 'version') {{
  $null = $config.model.PSObject.Properties.Remove('version')
}}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($stage3Config, ($config | ConvertTo-Json -Depth 100), $utf8NoBom)
$env:s2config_path = $stage3Config

Set-Location '{common_paths.gpt_sovits_root}'
& $pythonExe -s GPT_SoVITS/prepare_datasets/3-get-semantic.py

$partial = Join-Path $env:opt_dir '6-name2semantic-0.tsv'
$merged = Join-Path $env:opt_dir '6-name2semantic.tsv'
if (-not (Test-Path $partial -PathType Leaf)) {{
  throw "Stage 3 output not found: $partial"
}}
$semanticLines = @('item_name`tsemantic_audio') + (Get-Content $partial -Encoding UTF8)
[System.IO.File]::WriteAllLines($merged, $semanticLines, $utf8NoBom)
Remove-Item $partial -Force
if (Test-Path $stage3Config -PathType Leaf) {{
  Remove-Item $stage3Config -Force
}}
Write-Host "Prepared $merged"
"""


def _build_prepare_all_script() -> str:
    return """$ErrorActionPreference = 'Stop'

& (Join-Path $PSScriptRoot 'run-prepare-stage1.ps1')
& (Join-Path $PSScriptRoot 'run-prepare-stage2.ps1')
& (Join-Path $PSScriptRoot 'run-prepare-stage3.ps1')

Write-Host 'GPT-SoVITS dataset preparation finished.'
"""


def _build_train_gpt_script(*, gpt_sovits_root: Path, gpt_config_path: Path, gpu: str) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = '{gpt_sovits_root};{gpt_sovits_root / "GPT_SoVITS"}'
$env:_CUDA_VISIBLE_DEVICES = '{gpu}'
$env:hz = '25hz'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

Set-Location '{gpt_sovits_root}'
& $pythonExe -s GPT_SoVITS/s1_train.py --config_file '{gpt_config_path}'
"""


def _build_train_sovits_script(*, gpt_sovits_root: Path, sovits_config_path: Path, gpu: str) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = '{gpt_sovits_root};{gpt_sovits_root / "GPT_SoVITS"}'
$env:_CUDA_VISIBLE_DEVICES = '{gpu}'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

Set-Location '{gpt_sovits_root}'
& $pythonExe -s GPT_SoVITS/s2_train.py --config '{sovits_config_path}'
"""


def _build_train_all_script() -> str:
    return """$ErrorActionPreference = 'Stop'

& (Join-Path $PSScriptRoot 'run-train-gpt.ps1')
& (Join-Path $PSScriptRoot 'run-train-sovits.ps1')

Write-Host 'GPT-SoVITS training finished.'
"""


def _build_readme(
    *,
    speaker_name: str,
    speaker_alias: str,
    experiment_name: str,
    line_count: int,
) -> str:
    return (
        "# GPT-SoVITS 丛雨训练工作区\n\n"
        f"- 角色：`{speaker_name}`\n"
        f"- 训练别名：`{speaker_alias}`\n"
        f"- 实验名：`{experiment_name}`\n"
        f"- 样本数：`{line_count}`\n\n"
        "## 建议顺序\n\n"
        "1. 在已激活 `GPTSoVits` conda 环境的终端里运行 `scripts/run-prepare-all.ps1`\n"
        "2. 确认 `exp/<experiment>/` 下已经出现 `2-name2text.txt`、`4-cnhubert/`、`5-wav32k/`、`6-name2semantic.tsv`\n"
        "3. 运行 `scripts/run-train-gpt.ps1`\n"
        "4. GPT 训练稳定后，再运行 `scripts/run-train-sovits.ps1`\n\n"
        "## 说明\n\n"
        "- 这套工作区不会改动原始 galgame 音频\n"
        "- 训练脚本直接调用官方 GPT-SoVITS 的 `prepare_datasets` / `s1_train.py` / `s2_train.py`\n"
        "- 为了降低 Windows 路径编码风险，实验目录使用 ASCII 友好的名字\n"
    )
