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
    sovits_epochs: int = 6,
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
    train_gpt_launcher_path = scripts_dir / "train-gpt-launcher.py"
    train_gpt_script_path = scripts_dir / "run-train-gpt.ps1"
    train_sovits_launcher_path = scripts_dir / "train-sovits-launcher.py"
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
            train_gpt_launcher_path=train_gpt_launcher_path,
        ),
        encoding="utf-8",
        newline="\n",
    )
    train_gpt_launcher_path.write_text(
        _build_train_gpt_launcher(
            gpt_sovits_root=resolved_gpt_root,
            gpt_config_path=gpt_config_path,
            gpu=gpu,
        ),
        encoding="utf-8",
        newline="\n",
    )
    train_sovits_launcher_path.write_text(
        _build_train_sovits_launcher(
            gpt_sovits_root=resolved_gpt_root,
            sovits_config_path=sovits_config_path,
            gpu=gpu,
        ),
        encoding="utf-8",
        newline="\n",
    )
    train_sovits_script_path.write_text(
        _build_train_sovits_script(
            train_sovits_launcher_path=train_sovits_launcher_path,
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
$semanticLines = @("item_name`tsemantic_audio") + (Get-Content $partial -Encoding UTF8)
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
def _build_train_gpt_launcher(*, gpt_sovits_root: Path, gpt_config_path: Path, gpu: str) -> str:
    return f"""from __future__ import annotations

import math
import os
import platform
import sys
from collections import OrderedDict
from pathlib import Path


if "_CUDA_VISIBLE_DEVICES" in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = os.environ["_CUDA_VISIBLE_DEVICES"]

GPT_SOVITS_ROOT = Path({json.dumps(str(gpt_sovits_root))})
CONFIG_PATH = Path({json.dumps(str(gpt_config_path))})

sys.path.insert(0, str(GPT_SOVITS_ROOT))
sys.path.insert(0, str(GPT_SOVITS_ROOT / "GPT_SoVITS"))

import torch
from pytorch_lightning import Trainer, seed_everything
from pytorch_lightning.callbacks import Callback, ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger
from torch.utils.data import DataLoader

from AR.data.bucket_sampler import DistributedBucketSampler
from AR.data.data_module import Text2SemanticDataModule
from AR.models.t2s_lightning_module import Text2SemanticLightningModule
from AR.utils import get_newest_ckpt
from AR.utils.io import load_yaml_config
from process_ckpt import my_save


STEP_LOG_INTERVAL = 50


def _metric_to_float(value):
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class _ProgressPrinter(Callback):
    def __init__(self, step_interval: int = STEP_LOG_INTERVAL):
        self.step_interval = max(step_interval, 1)

    def on_train_start(self, trainer, pl_module):
        total_batches = trainer.num_training_batches
        if isinstance(total_batches, float) and not math.isfinite(total_batches):
            total_batches = "?"
        print(f"Training started: epochs={{trainer.max_epochs}}, batches_per_epoch={{total_batches}}")

    def on_train_epoch_start(self, trainer, pl_module):
        print(f"Epoch {{trainer.current_epoch + 1}}/{{trainer.max_epochs}} started")

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        total_batches = trainer.num_training_batches
        if isinstance(total_batches, float) and not math.isfinite(total_batches):
            total_batches = None
        current_batch = batch_idx + 1
        if total_batches is not None:
            should_log = current_batch % self.step_interval == 0 or current_batch == int(total_batches)
        else:
            should_log = current_batch % self.step_interval == 0
        if not should_log:
            return

        metrics = trainer.callback_metrics
        loss = _metric_to_float(metrics.get("total_loss_step", metrics.get("total_loss")))
        acc = _metric_to_float(metrics.get("top_3_acc_step", metrics.get("top_3_acc")))
        lr = _metric_to_float(metrics.get("lr"))

        batch_part = f"{{current_batch}}/{{int(total_batches)}}" if total_batches is not None else str(current_batch)
        parts = [f"Epoch {{trainer.current_epoch + 1}}", f"batch {{batch_part}}", f"global_step {{trainer.global_step}}"]
        if loss is not None:
            parts.append(f"loss {{loss:.4f}}")
        if acc is not None:
            parts.append(f"acc {{acc:.4f}}")
        if lr is not None:
            parts.append(f"lr {{lr:.6f}}")
        print(" | ".join(parts))

    def on_train_epoch_end(self, trainer, pl_module):
        print(f"Epoch {{trainer.current_epoch + 1}}/{{trainer.max_epochs}} finished")

    def on_train_end(self, trainer, pl_module):
        print("Training ended.")


class _SingleGpuText2SemanticDataModule(Text2SemanticDataModule):
    def train_dataloader(self):
        batch_size = (
            self.config["train"]["batch_size"] // 2
            if self.config["train"].get("if_dpo", False) is True
            else self.config["train"]["batch_size"]
        )
        batch_size = max(min(batch_size, len(self._train_dataset) // 4), 1)
        sampler = DistributedBucketSampler(self._train_dataset, num_replicas=1, rank=0, batch_size=batch_size)
        num_workers = 0 if platform.system() == "Windows" else self.num_workers
        kwargs = {{
            "batch_size": batch_size,
            "sampler": sampler,
            "collate_fn": self._train_dataset.collate,
            "num_workers": num_workers,
            "persistent_workers": num_workers > 0,
        }}
        if num_workers > 0:
            kwargs["prefetch_factor"] = 16
        return DataLoader(self._train_dataset, **kwargs)

    def val_dataloader(self):
        num_workers = 0 if platform.system() == "Windows" else max(self.num_workers, 12)
        kwargs = {{
            "batch_size": 1,
            "shuffle": False,
            "collate_fn": self._train_dataset.collate,
            "num_workers": num_workers,
            "persistent_workers": num_workers > 0,
        }}
        if num_workers > 0:
            kwargs["prefetch_factor"] = 16
        return DataLoader(self._dev_dataset, **kwargs)


class _ModelCheckpoint(ModelCheckpoint):
    def __init__(
        self,
        config,
        if_save_latest,
        if_save_every_weights,
        half_weights_save_dir,
        exp_name,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.if_save_latest = if_save_latest
        self.if_save_every_weights = if_save_every_weights
        self.half_weights_save_dir = half_weights_save_dir
        self.exp_name = exp_name
        self.config = config

    def on_train_epoch_end(self, trainer, pl_module):
        if self._should_save_on_train_epoch_end(trainer):
            monitor_candidates = self._monitor_candidates(trainer)
            if self._every_n_epochs >= 1 and (trainer.current_epoch + 1) % self._every_n_epochs == 0:
                if self.if_save_latest is True:
                    to_clean = list(os.listdir(self.dirpath))
                self._save_topk_checkpoint(trainer, monitor_candidates)
                if self.if_save_latest is True:
                    for name in to_clean:
                        try:
                            os.remove(f"{{self.dirpath}}/{{name}}")
                        except OSError:
                            pass
                if self.if_save_every_weights is True:
                    to_save_od = OrderedDict()
                    to_save_od["weight"] = OrderedDict()
                    dictt = trainer.strategy._lightning_module.state_dict()
                    for key in dictt:
                        to_save_od["weight"][key] = dictt[key].half()
                    to_save_od["config"] = self.config
                    to_save_od["info"] = f"GPT-e{{trainer.current_epoch + 1}}"
                    if os.environ.get("LOCAL_RANK", "0") == "0":
                        my_save(
                            to_save_od,
                            f"{{self.half_weights_save_dir}}/{{self.exp_name}}-e{{trainer.current_epoch + 1}}.ckpt",
                        )
            self._save_last_checkpoint(trainer, monitor_candidates)


def main():
    config = load_yaml_config(str(CONFIG_PATH))

    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    ckpt_dir = output_dir / "ckpt"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    seed_everything(config["train"]["seed"], workers=True)

    ckpt_callback = _ModelCheckpoint(
        config=config,
        if_save_latest=config["train"]["if_save_latest"],
        if_save_every_weights=config["train"]["if_save_every_weights"],
        half_weights_save_dir=config["train"]["half_weights_save_dir"],
        exp_name=config["train"]["exp_name"],
        save_top_k=-1,
        monitor="top_3_acc",
        mode="max",
        save_on_train_epoch_end=True,
        every_n_epochs=config["train"]["save_every_n_epoch"],
        dirpath=ckpt_dir,
    )
    logger = TensorBoardLogger(name=output_dir.stem, save_dir=output_dir)

    trainer = Trainer(
        max_epochs=config["train"]["epochs"],
        accelerator="gpu" if torch.cuda.is_available() else "cpu",
        devices=1 if torch.cuda.is_available() else 1,
        benchmark=False,
        fast_dev_run=False,
        strategy="auto",
        precision=config["train"]["precision"],
        logger=logger,
        num_sanity_val_steps=0,
        callbacks=[ckpt_callback, _ProgressPrinter()],
        use_distributed_sampler=False,
        limit_val_batches=0,
        enable_progress_bar=False,
    )

    model = Text2SemanticLightningModule(config, output_dir)
    data_module = _SingleGpuText2SemanticDataModule(
        config,
        train_semantic_path=config["train_semantic_path"],
        train_phoneme_path=config["train_phoneme_path"],
    )

    try:
        newest_ckpt_name = get_newest_ckpt(os.listdir(ckpt_dir))
        ckpt_path = ckpt_dir / newest_ckpt_name
    except Exception:
        ckpt_path = None

    print("ckpt_path:", ckpt_path)
    trainer.fit(model, data_module, ckpt_path=ckpt_path)
    print("GPT training finished.")


if __name__ == "__main__":
    main()
"""


def _build_train_gpt_script(*, train_gpt_launcher_path: Path) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:hz = '25hz'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

& $pythonExe -s '{train_gpt_launcher_path}'
"""


def _build_train_sovits_launcher(*, gpt_sovits_root: Path, sovits_config_path: Path, gpu: str) -> str:
    return f"""from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path


if "_CUDA_VISIBLE_DEVICES" in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = os.environ["_CUDA_VISIBLE_DEVICES"]
else:
    os.environ["CUDA_VISIBLE_DEVICES"] = {json.dumps(gpu)}

GPT_SOVITS_ROOT = Path({json.dumps(str(gpt_sovits_root))})
CONFIG_PATH = Path({json.dumps(str(sovits_config_path))})

sys.path.insert(0, str(GPT_SOVITS_ROOT))
sys.path.insert(0, str(GPT_SOVITS_ROOT / "GPT_SoVITS"))

import torch
from torch.cuda.amp import GradScaler, autocast
from torch.nn import functional as F
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

import utils
from module import commons
from module.data_utils import DistributedBucketSampler, TextAudioSpeakerCollate, TextAudioSpeakerLoader
from module.losses import discriminator_loss, feature_loss, generator_loss, kl_loss
from module.mel_processing import mel_spectrogram_torch, spec_to_mel_torch
from module.models import MultiPeriodDiscriminator, SynthesizerTrn
from process_ckpt import savee


logging.getLogger("matplotlib").setLevel(logging.INFO)
logging.getLogger("h5py").setLevel(logging.INFO)
logging.getLogger("numba").setLevel(logging.INFO)

torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = False
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.set_float32_matmul_precision("medium")

BOUNDARIES = [
    32,
    300,
    400,
    500,
    600,
    700,
    800,
    900,
    1000,
    1100,
    1200,
    1300,
    1400,
    1500,
    1600,
    1700,
    1800,
    1900,
]


def _to_float(value):
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _move_to_device(tensor, device):
    if tensor is None:
        return None
    return tensor.to(device, non_blocking=torch.cuda.is_available())


def _build_train_loader(hps):
    train_dataset = TextAudioSpeakerLoader(hps.data, version=hps.model.version)
    train_sampler = DistributedBucketSampler(
        train_dataset,
        hps.train.batch_size,
        BOUNDARIES,
        num_replicas=1,
        rank=0,
        shuffle=True,
    )
    collate_fn = TextAudioSpeakerCollate(version=hps.model.version)
    num_workers = 0 if platform.system() == "Windows" else 5
    kwargs = {{
        "shuffle": False,
        "pin_memory": torch.cuda.is_available(),
        "collate_fn": collate_fn,
        "batch_sampler": train_sampler,
        "num_workers": num_workers,
        "persistent_workers": num_workers > 0,
    }}
    if num_workers > 0:
        kwargs["prefetch_factor"] = 3
    train_loader = DataLoader(train_dataset, **kwargs)
    return train_loader, train_sampler


def _build_models_and_optimizers(hps, device):
    net_g = SynthesizerTrn(
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        n_speakers=hps.data.n_speakers,
        **hps.model,
    ).to(device)
    net_d = MultiPeriodDiscriminator(hps.model.use_spectral_norm, version=hps.model.version).to(device)

    te_p = list(map(id, net_g.enc_p.text_embedding.parameters()))
    et_p = list(map(id, net_g.enc_p.encoder_text.parameters()))
    mrte_p = list(map(id, net_g.enc_p.mrte.parameters()))
    base_params = filter(
        lambda p: id(p) not in te_p + et_p + mrte_p and p.requires_grad,
        net_g.parameters(),
    )

    optim_g = torch.optim.AdamW(
        [
            {{"params": base_params, "lr": hps.train.learning_rate}},
            {{
                "params": net_g.enc_p.text_embedding.parameters(),
                "lr": hps.train.learning_rate * hps.train.text_low_lr_rate,
            }},
            {{
                "params": net_g.enc_p.encoder_text.parameters(),
                "lr": hps.train.learning_rate * hps.train.text_low_lr_rate,
            }},
            {{
                "params": net_g.enc_p.mrte.parameters(),
                "lr": hps.train.learning_rate * hps.train.text_low_lr_rate,
            }},
        ],
        hps.train.learning_rate,
        betas=hps.train.betas,
        eps=hps.train.eps,
    )
    optim_d = torch.optim.AdamW(
        net_d.parameters(),
        hps.train.learning_rate,
        betas=hps.train.betas,
        eps=hps.train.eps,
    )

    return net_g, net_d, optim_g, optim_d


def _maybe_resume_or_load_pretrained(hps, net_g, net_d, optim_g, optim_d, train_loader, logger):
    logs_dir = Path(hps.data.exp_dir) / f"logs_s2_{{hps.model.version}}"
    logs_dir.mkdir(parents=True, exist_ok=True)
    epoch_str = 1
    global_step = 0

    try:
        d_ckpt = utils.latest_checkpoint_path(str(logs_dir), "D_*.pth")
        utils.load_checkpoint(d_ckpt, net_d, optim_d)
        logger.info("loaded D checkpoint")
        g_ckpt = utils.latest_checkpoint_path(str(logs_dir), "G_*.pth")
        _, _, _, epoch_str = utils.load_checkpoint(g_ckpt, net_g, optim_g)
        epoch_str += 1
        global_step = (epoch_str - 1) * len(train_loader)
    except Exception:
        epoch_str = 1
        global_step = 0
        if hps.train.pretrained_s2G and os.path.exists(hps.train.pretrained_s2G):
            logger.info("loaded pretrained %s", hps.train.pretrained_s2G)
            print(
                "loaded pretrained %s" % hps.train.pretrained_s2G,
                net_g.load_state_dict(
                    torch.load(hps.train.pretrained_s2G, map_location="cpu", weights_only=False)["weight"],
                    strict=False,
                ),
            )
        if hps.train.pretrained_s2D and os.path.exists(hps.train.pretrained_s2D):
            logger.info("loaded pretrained %s", hps.train.pretrained_s2D)
            print(
                "loaded pretrained %s" % hps.train.pretrained_s2D,
                net_d.load_state_dict(
                    torch.load(hps.train.pretrained_s2D, map_location="cpu", weights_only=False)["weight"],
                    strict=False,
                ),
            )

    return logs_dir, epoch_str, global_step


def _train_epoch(epoch, hps, device, net_g, net_d, optim_g, optim_d, scaler, train_loader, train_sampler, logger, writer, global_step):
    train_sampler.set_epoch(epoch)
    net_g.train()
    net_d.train()

    total_batches = len(train_loader)
    print(f"Epoch {{epoch}}/{{hps.train.epochs}} started")

    for batch_idx, data in enumerate(train_loader, start=1):
        if hps.model.version in {{"v2Pro", "v2ProPlus"}}:
            ssl, ssl_lengths, spec, spec_lengths, y, y_lengths, text, text_lengths, sv_emb = data
        else:
            ssl, ssl_lengths, spec, spec_lengths, y, y_lengths, text, text_lengths = data
            sv_emb = None

        spec = _move_to_device(spec, device)
        spec_lengths = _move_to_device(spec_lengths, device)
        y = _move_to_device(y, device)
        y_lengths = _move_to_device(y_lengths, device)
        ssl = _move_to_device(ssl, device)
        ssl.requires_grad = False
        text = _move_to_device(text, device)
        text_lengths = _move_to_device(text_lengths, device)
        if sv_emb is not None:
            sv_emb = _move_to_device(sv_emb, device)

        with autocast(enabled=hps.train.fp16_run):
            if hps.model.version in {{"v2Pro", "v2ProPlus"}}:
                (
                    y_hat,
                    kl_ssl,
                    ids_slice,
                    x_mask,
                    z_mask,
                    (z, z_p, m_p, logs_p, m_q, logs_q),
                    stats_ssl,
                ) = net_g(ssl, spec, spec_lengths, text, text_lengths, sv_emb)
            else:
                (
                    y_hat,
                    kl_ssl,
                    ids_slice,
                    x_mask,
                    z_mask,
                    (z, z_p, m_p, logs_p, m_q, logs_q),
                    stats_ssl,
                ) = net_g(ssl, spec, spec_lengths, text, text_lengths)

            mel = spec_to_mel_torch(
                spec,
                hps.data.filter_length,
                hps.data.n_mel_channels,
                hps.data.sampling_rate,
                hps.data.mel_fmin,
                hps.data.mel_fmax,
            )
            y_mel = commons.slice_segments(mel, ids_slice, hps.train.segment_size // hps.data.hop_length)
            y_hat_mel = mel_spectrogram_torch(
                y_hat.squeeze(1),
                hps.data.filter_length,
                hps.data.n_mel_channels,
                hps.data.sampling_rate,
                hps.data.hop_length,
                hps.data.win_length,
                hps.data.mel_fmin,
                hps.data.mel_fmax,
            )
            y_slice = commons.slice_segments(y, ids_slice * hps.data.hop_length, hps.train.segment_size)
            y_d_hat_r, y_d_hat_g, _, _ = net_d(y_slice, y_hat.detach())
            with autocast(enabled=False):
                loss_disc, _, _ = discriminator_loss(y_d_hat_r, y_d_hat_g)
                loss_disc_all = loss_disc

        optim_d.zero_grad()
        scaler.scale(loss_disc_all).backward()
        scaler.unscale_(optim_d)
        grad_norm_d = commons.clip_grad_value_(net_d.parameters(), None)
        scaler.step(optim_d)

        with autocast(enabled=hps.train.fp16_run):
            y_d_hat_r, y_d_hat_g, fmap_r, fmap_g = net_d(y_slice, y_hat)
            with autocast(enabled=False):
                loss_mel = F.l1_loss(y_mel, y_hat_mel) * hps.train.c_mel
                loss_kl = kl_loss(z_p, logs_q, m_p, logs_p, z_mask) * hps.train.c_kl
                loss_fm = feature_loss(fmap_r, fmap_g)
                loss_gen, _ = generator_loss(y_d_hat_g)
                loss_gen_all = loss_gen + loss_fm + loss_mel + kl_ssl + loss_kl

        optim_g.zero_grad()
        scaler.scale(loss_gen_all).backward()
        scaler.unscale_(optim_g)
        grad_norm_g = commons.clip_grad_value_(net_g.parameters(), None)
        scaler.step(optim_g)
        scaler.update()

        if global_step % hps.train.log_interval == 0:
            lr = optim_g.param_groups[0]["lr"]
            logger.info(
                "Train Epoch: %s [%.0f%%]",
                epoch,
                100.0 * (batch_idx - 1) / max(total_batches, 1),
            )
            logger.info(
                [
                    loss_disc.item(),
                    loss_gen.item(),
                    loss_fm.item(),
                    loss_mel.item(),
                    kl_ssl.item(),
                    loss_kl.item(),
                    global_step,
                    lr,
                ]
            )
            print(
                " | ".join(
                    [
                        f"Epoch {{epoch}}",
                        f"batch {{batch_idx}}/{{total_batches}}",
                        f"global_step {{global_step}}",
                        f"loss_g {{loss_gen_all.item():.4f}}",
                        f"loss_d {{loss_disc_all.item():.4f}}",
                        f"mel {{loss_mel.item():.4f}}",
                        f"lr {{lr:.6f}}",
                    ]
                )
            )
            scalar_dict = {{
                "loss/g/total": loss_gen_all,
                "loss/d/total": loss_disc_all,
                "learning_rate": lr,
                "grad_norm_d": grad_norm_d,
                "grad_norm_g": grad_norm_g,
                "loss/g/fm": loss_fm,
                "loss/g/mel": loss_mel,
                "loss/g/kl_ssl": kl_ssl,
                "loss/g/kl": loss_kl,
            }}
            utils.summarize(writer=writer, global_step=global_step, scalars=scalar_dict)

        global_step += 1

    print(f"Epoch {{epoch}}/{{hps.train.epochs}} finished")
    logger.info("====> Epoch: %s", epoch)
    return global_step


def _save_epoch_artifacts(epoch, hps, net_g, net_d, optim_g, optim_d, logger, global_step):
    logs_dir = Path(hps.data.exp_dir) / f"logs_s2_{{hps.model.version}}"
    logs_dir.mkdir(parents=True, exist_ok=True)
    if epoch % hps.train.save_every_epoch != 0:
        return

    if hps.train.if_save_latest == 0:
        g_path = logs_dir / f"G_{{global_step}}.pth"
        d_path = logs_dir / f"D_{{global_step}}.pth"
    else:
        g_path = logs_dir / "G_233333333333.pth"
        d_path = logs_dir / "D_233333333333.pth"

    utils.save_checkpoint(net_g, optim_g, hps.train.learning_rate, epoch, str(g_path))
    utils.save_checkpoint(net_d, optim_d, hps.train.learning_rate, epoch, str(d_path))

    if hps.train.if_save_every_weights:
        ckpt = net_g.state_dict()
        result = savee(
            ckpt,
            f"{{hps.name}}_e{{epoch}}_s{{global_step}}",
            epoch,
            global_step,
            hps,
            model_version=None if hps.model.version not in {{"v2Pro", "v2ProPlus"}} else hps.model.version,
        )
        logger.info("saving ckpt %s_e%s:%s", hps.name, epoch, result)


def main():
    hps = utils.get_hparams_from_file(str(CONFIG_PATH))
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    logs_dir = Path(hps.data.exp_dir) / f"logs_s2_{{hps.model.version}}"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = utils.get_logger(hps.data.exp_dir)
    logger.info(hps)
    writer = SummaryWriter(log_dir=hps.s2_ckpt_dir)
    SummaryWriter(log_dir=os.path.join(hps.s2_ckpt_dir, "eval")).close()

    torch.manual_seed(hps.train.seed)

    train_loader, train_sampler = _build_train_loader(hps)
    net_g, net_d, optim_g, optim_d = _build_models_and_optimizers(hps, device)
    _, epoch_str, global_step = _maybe_resume_or_load_pretrained(
        hps,
        net_g,
        net_d,
        optim_g,
        optim_d,
        train_loader,
        logger,
    )

    scheduler_g = torch.optim.lr_scheduler.ExponentialLR(
        optim_g,
        gamma=hps.train.lr_decay,
        last_epoch=-1,
    )
    scheduler_d = torch.optim.lr_scheduler.ExponentialLR(
        optim_d,
        gamma=hps.train.lr_decay,
        last_epoch=-1,
    )
    for _ in range(epoch_str):
        scheduler_g.step()
        scheduler_d.step()

    scaler = GradScaler(enabled=hps.train.fp16_run)

    print(f"Training started: epochs={{hps.train.epochs}}, batches_per_epoch={{len(train_loader)}}")
    print("start training from epoch %s" % epoch_str)
    for epoch in range(epoch_str, hps.train.epochs + 1):
        global_step = _train_epoch(
            epoch,
            hps,
            device,
            net_g,
            net_d,
            optim_g,
            optim_d,
            scaler,
            train_loader,
            train_sampler,
            logger,
            writer,
            global_step,
        )
        _save_epoch_artifacts(epoch, hps, net_g, net_d, optim_g, optim_d, logger, global_step)
        scheduler_g.step()
        scheduler_d.step()

    writer.close()
    print("Training ended.")
    print("SoVITS training finished.")


if __name__ == "__main__":
    main()
"""


def _build_train_sovits_script(*, train_sovits_launcher_path: Path) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

& $pythonExe -s '{train_sovits_launcher_path}'
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
