from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from duolingal.core.gptsovits_batch import prepare_gptsovits_batch
from duolingal.core.gptsovits_reinject import _convert_wav_to_ogg
from duolingal.core.gptsovits_training import prepare_gptsovits_training
from duolingal.core.patching import prepare_patch_staging
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import (
    GptSovitsProductionPreparationResult,
    GptSovitsProductionRunResult,
    GptSovitsProductionRunSpeakerStatus,
    GptSovitsProductionSpeakerPlan,
)


def prepare_gptsovits_production(
    project_root: str | Path,
    *,
    speakers: list[str] | None = None,
    min_lines: int = 1,
    gpt_sovits_root: str | Path | None = None,
    reference_mode: str = "auto",
    inference_limit: int | None = None,
    target_sample_rate: int = 48000,
    api_port: int = 9880,
    sync_game_root: bool = False,
    gpt_epochs: int = 12,
    sovits_epochs: int = 6,
    gpt_batch_size: int = 4,
    sovits_batch_size: int = 4,
) -> GptSovitsProductionPreparationResult:
    if min_lines < 1:
        raise ValueError("Minimum line count must be at least 1.")
    if inference_limit is not None and inference_limit < 1:
        raise ValueError("Inference limit must be at least 1 when provided.")

    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    resolved_repo_root = resolved_project_root.parents[2]
    dataset_root = resolved_project_root / "tts-dataset"
    if not dataset_root.exists():
        raise ValueError(f"TTS dataset root does not exist: {dataset_root}")

    selected_speakers = _select_speakers(
        dataset_root,
        requested_speakers=speakers or [],
        min_lines=min_lines,
    )
    if not selected_speakers:
        raise ValueError("No speaker datasets matched the requested production criteria.")

    production_name = _derive_production_name(selected_speakers, explicit_speakers=speakers or [])
    production_root = resolved_project_root / "tts-production" / production_name
    scripts_dir = production_root / "scripts"
    logs_dir = production_root / "logs"
    combined_override_root = production_root / "game-ready" / "unencrypted"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    combined_override_root.mkdir(parents=True, exist_ok=True)

    speaker_plans: list[GptSovitsProductionSpeakerPlan] = []
    resolved_gpt_root: Path | None = None
    for speaker in selected_speakers:
        training_result = prepare_gptsovits_training(
            resolved_project_root,
            speaker["speaker_name"],
            gpt_sovits_root=gpt_sovits_root,
            gpt_epochs=gpt_epochs,
            sovits_epochs=sovits_epochs,
            gpt_batch_size=gpt_batch_size,
            sovits_batch_size=sovits_batch_size,
        )
        current_gpt_root = Path(training_result.gpt_sovits_root).resolve()
        if resolved_gpt_root is None:
            resolved_gpt_root = current_gpt_root
        elif current_gpt_root != resolved_gpt_root:
            raise ValueError("All production speakers must resolve to the same GPT-SoVITS root.")
        batch_limit = min(speaker["preview_count"], inference_limit) if inference_limit is not None else speaker["preview_count"]
        speaker_plans.append(
            GptSovitsProductionSpeakerPlan(
                speaker_name=speaker["speaker_name"],
                line_count=speaker["line_count"],
                preview_count=speaker["preview_count"],
                batch_limit=batch_limit,
                experiment_name=training_result.experiment_name,
                training_root=training_result.training_root,
                prepare_all_script_path=training_result.prepare_all_script_path,
                train_gpt_script_path=training_result.train_gpt_script_path,
                train_sovits_script_path=training_result.train_sovits_script_path,
                gpt_weights_dir=str(Path(training_result.training_root) / "weights" / "gpt"),
                sovits_weights_dir=str(Path(training_result.training_root) / "weights" / "sovits"),
            )
        )

    queue_path = production_root / "production-plan.json"
    run_script_path = scripts_dir / "run-production.ps1"
    readme_path = production_root / "README.zh-CN.md"
    assert resolved_gpt_root is not None

    queue_payload = {
        "project_root": str(resolved_project_root),
        "repo_root": str(resolved_repo_root),
        "production_root": str(production_root),
        "game_root": manifest.root_path,
        "gpt_sovits_root": str(resolved_gpt_root),
        "reference_mode": reference_mode,
        "target_sample_rate": target_sample_rate,
        "api_port": api_port,
        "sync_game_root": sync_game_root,
        "gpt_epochs": gpt_epochs,
        "sovits_epochs": sovits_epochs,
        "combined_override_root": str(combined_override_root),
        "logs_dir": str(logs_dir),
        "speakers": [plan.model_dump(mode="json", exclude_none=True) for plan in speaker_plans],
    }
    queue_path.write_text(json.dumps(queue_payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    run_script_path.write_text(
        _build_run_script(queue_path, resolved_repo_root=resolved_repo_root),
        encoding="utf-8",
        newline="\n",
    )
    readme_path.write_text(
        _build_production_readme(
            speaker_count=len(speaker_plans),
            reference_mode=reference_mode,
            inference_limit=inference_limit,
            sync_game_root=sync_game_root,
        ),
        encoding="utf-8",
        newline="\n",
    )

    return GptSovitsProductionPreparationResult(
        project_root=str(resolved_project_root),
        production_root=str(production_root),
        queue_path=str(queue_path),
        run_script_path=str(run_script_path),
        readme_path=str(readme_path),
        combined_override_root=str(combined_override_root),
        api_port=api_port,
        sync_game_root=sync_game_root,
        speaker_count=len(speaker_plans),
        speakers=speaker_plans,
        notes=[
            "Run the generated scripts/run-production.ps1 inside the GPTSoVits conda environment.",
            "The production runner is resumable: completed speakers are tracked in production-state.json.",
            "A combined game-ready override tree is accumulated under tts-production/<plan>/game-ready/unencrypted.",
        ],
    )


def run_gptsovits_production(production_root: str | Path) -> GptSovitsProductionRunResult:
    resolved_production_root = Path(production_root).expanduser().resolve()
    queue_path = resolved_production_root / "production-plan.json"
    if not queue_path.exists():
        raise ValueError(f"Production plan does not exist: {queue_path}")

    plan = json.loads(queue_path.read_text(encoding="utf-8"))
    project_root = Path(plan["project_root"]).resolve()
    combined_override_root = Path(plan["combined_override_root"]).resolve()
    combined_override_root.mkdir(parents=True, exist_ok=True)
    logs_dir = Path(plan["logs_dir"]).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)
    state_path = resolved_production_root / "production-state.json"
    status_path = resolved_production_root / "production-status.txt"
    total_speakers = len(plan["speakers"])

    state = _load_state(state_path)
    completed_names = {item["speaker_name"] for item in state.get("completed_speakers", [])}
    completed_speakers: list[GptSovitsProductionRunSpeakerStatus] = [
        GptSovitsProductionRunSpeakerStatus(**item) for item in state.get("completed_speakers", [])
    ]

    external_api = _api_ready(plan["api_port"])
    print(f"[queue] Plan: {resolved_production_root.name}")
    print(
        f"[queue] Speakers total={total_speakers}, completed={len(completed_speakers)}, remaining={total_speakers - len(completed_speakers)}"
    )
    print(f"[queue] GPT-SoVITS api_v2 already running: {external_api}")
    _write_state(
        state_path,
        completed_speakers,
        total_speakers=total_speakers,
        current_speaker=None,
        current_stage="queue-start",
        last_event="Production queue started.",
        status_path=status_path,
    )

    for speaker_index, speaker_plan in enumerate(plan["speakers"], start=1):
        speaker_name = str(speaker_plan["speaker_name"])
        if speaker_name in completed_names:
            print(f"[queue] [{speaker_index}/{total_speakers}] Skip completed speaker: {speaker_name}")
            continue

        experiment_name = str(speaker_plan["experiment_name"])
        training_root = Path(speaker_plan["training_root"]).resolve()
        exp_dir = training_root / "exp" / experiment_name
        print(f"[queue] [{speaker_index}/{total_speakers}] Speaker: {speaker_name} ({experiment_name})")
        _write_state(
            state_path,
            completed_speakers,
            total_speakers=total_speakers,
            current_speaker=speaker_name,
            current_stage="prepare-check",
            last_event=f"Checking preparation outputs for {speaker_name}.",
            status_path=status_path,
        )
        if not (exp_dir / "6-name2semantic.tsv").exists():
            print(f"[queue] [{speaker_index}/{total_speakers}] Stage prepare -> running official dataset prep")
            _write_state(
                state_path,
                completed_speakers,
                total_speakers=total_speakers,
                current_speaker=speaker_name,
                current_stage="prepare",
                last_event=f"Running dataset preparation for {speaker_name}.",
                status_path=status_path,
            )
            _run_powershell_script(
                Path(speaker_plan["prepare_all_script_path"]),
                logs_dir / f"{experiment_name}-prepare.log",
                label=f"{speaker_name} prepare",
            )
        else:
            print(f"[queue] [{speaker_index}/{total_speakers}] Stage prepare -> already complete")

        gpt_weight_path = _find_gpt_weight(
            Path(speaker_plan["gpt_weights_dir"]),
            experiment_name=experiment_name,
            epoch=plan["gpt_epochs"],
        )
        if gpt_weight_path is None:
            print(f"[queue] [{speaker_index}/{total_speakers}] Stage GPT -> training to e{plan['gpt_epochs']}")
            _write_state(
                state_path,
                completed_speakers,
                total_speakers=total_speakers,
                current_speaker=speaker_name,
                current_stage="train-gpt",
                last_event=f"Training GPT for {speaker_name}.",
                status_path=status_path,
            )
            _run_powershell_script(
                Path(speaker_plan["train_gpt_script_path"]),
                logs_dir / f"{experiment_name}-gpt.log",
                label=f"{speaker_name} GPT",
            )
            gpt_weight_path = _find_gpt_weight(
                Path(speaker_plan["gpt_weights_dir"]),
                experiment_name=experiment_name,
                epoch=plan["gpt_epochs"],
            )
        if gpt_weight_path is None:
            raise ValueError(f"Expected GPT weight was not found for speaker {speaker_name}.")
        print(f"[queue] [{speaker_index}/{total_speakers}] Stage GPT -> ready ({gpt_weight_path.name})")

        sovits_weight_path = _find_sovits_weight(
            Path(speaker_plan["sovits_weights_dir"]),
            experiment_name=experiment_name,
            epoch=plan["sovits_epochs"],
        )
        if sovits_weight_path is None:
            print(f"[queue] [{speaker_index}/{total_speakers}] Stage SoVITS -> training to e{plan['sovits_epochs']}")
            _write_state(
                state_path,
                completed_speakers,
                total_speakers=total_speakers,
                current_speaker=speaker_name,
                current_stage="train-sovits",
                last_event=f"Training SoVITS for {speaker_name}.",
                status_path=status_path,
            )
            _run_powershell_script(
                Path(speaker_plan["train_sovits_script_path"]),
                logs_dir / f"{experiment_name}-sovits.log",
                label=f"{speaker_name} SoVITS",
            )
            sovits_weight_path = _find_sovits_weight(
                Path(speaker_plan["sovits_weights_dir"]),
                experiment_name=experiment_name,
                epoch=plan["sovits_epochs"],
            )
        if sovits_weight_path is None:
            raise ValueError(f"Expected SoVITS weight was not found for speaker {speaker_name}.")
        print(f"[queue] [{speaker_index}/{total_speakers}] Stage SoVITS -> ready ({sovits_weight_path.name})")

        print(
            f"[queue] [{speaker_index}/{total_speakers}] Stage batch -> preparing {speaker_plan['batch_limit']} English lines"
        )
        _write_state(
            state_path,
            completed_speakers,
            total_speakers=total_speakers,
            current_speaker=speaker_name,
            current_stage="prepare-batch",
            last_event=f"Preparing GPT-SoVITS batch for {speaker_name}.",
            status_path=status_path,
        )
        batch_result = prepare_gptsovits_batch(
            project_root,
            speaker_name,
            limit=int(speaker_plan["batch_limit"]),
            reference_mode=plan["reference_mode"],
        )

        speaker_api_process = None
        try:
            if not external_api:
                print(f"[queue] [{speaker_index}/{total_speakers}] Stage api -> starting temporary api_v2")
                _write_state(
                    state_path,
                    completed_speakers,
                    total_speakers=total_speakers,
                    current_speaker=speaker_name,
                    current_stage="start-api",
                    last_event=f"Starting GPT-SoVITS api_v2 for {speaker_name}.",
                    status_path=status_path,
                )
                speaker_api_process = _start_api_server(plan, logs_dir, label=experiment_name)

            print(f"[queue] [{speaker_index}/{total_speakers}] Stage infer -> switching weights")
            _set_weight(plan["api_port"], "set_gpt_weights", gpt_weight_path)
            _set_weight(plan["api_port"], "set_sovits_weights", sovits_weight_path)
            print(f"[queue] [{speaker_index}/{total_speakers}] Stage infer -> synthesizing batch")
            _write_state(
                state_path,
                completed_speakers,
                total_speakers=total_speakers,
                current_speaker=speaker_name,
                current_stage="infer",
                last_event=f"Synthesizing {batch_result.item_count} lines for {speaker_name}.",
                status_path=status_path,
            )
            _synthesize_batch(Path(batch_result.batch_dir), plan["api_port"])
            print(f"[queue] [{speaker_index}/{total_speakers}] Stage convert -> converting WAV to OGG")
            _write_state(
                state_path,
                completed_speakers,
                total_speakers=total_speakers,
                current_speaker=speaker_name,
                current_stage="convert",
                last_event=f"Converting synthesized WAV files for {speaker_name}.",
                status_path=status_path,
            )
            converted_count = _merge_batch_outputs_into_override(
                Path(batch_result.batch_dir),
                combined_override_root,
                target_sample_rate=int(plan["target_sample_rate"]),
            )
        finally:
            if speaker_api_process is not None:
                speaker_api_process.terminate()
                try:
                    speaker_api_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    speaker_api_process.kill()

        status = GptSovitsProductionRunSpeakerStatus(
            speaker_name=speaker_name,
            experiment_name=experiment_name,
            batch_dir=batch_result.batch_dir,
            generated_count=batch_result.item_count,
            converted_count=converted_count,
            gpt_weight_path=str(gpt_weight_path),
            sovits_weight_path=str(sovits_weight_path),
        )
        completed_speakers.append(status)
        completed_names.add(speaker_name)
        print(
            f"[queue] [{speaker_index}/{total_speakers}] Speaker complete -> generated={batch_result.item_count}, converted={converted_count}"
        )
        _write_state(
            state_path,
            completed_speakers,
            total_speakers=total_speakers,
            current_speaker=None,
            current_stage="speaker-complete",
            last_event=f"Completed speaker {speaker_name}.",
            status_path=status_path,
        )

    print("[queue] Rebuilding combined patch staging from completed speakers")
    _write_state(
        state_path,
        completed_speakers,
        total_speakers=total_speakers,
        current_speaker=None,
        current_stage="patch-build",
        last_event="Rebuilding project patch staging from combined overrides.",
        status_path=status_path,
    )
    patch_result = prepare_patch_staging(project_root, combined_override_root, archive_name=None)
    synced_game_root = None
    if plan.get("sync_game_root"):
        print("[queue] Syncing combined overrides into the real game root")
        _write_state(
            state_path,
            completed_speakers,
            total_speakers=total_speakers,
            current_speaker=None,
            current_stage="sync-game-root",
            last_event="Syncing combined overrides into the game root.",
            status_path=status_path,
        )
        synced_game_root = _sync_game_root(Path(plan["game_root"]), combined_override_root)
    print(
        f"[queue] Production complete -> speakers={len(completed_speakers)}, patch={patch_result.archive_name}, sync_game_root={bool(synced_game_root)}"
    )
    _write_state(
        state_path,
        completed_speakers,
        total_speakers=total_speakers,
        current_speaker=None,
        current_stage="completed",
        last_event="Production queue completed.",
        status_path=status_path,
    )

    return GptSovitsProductionRunResult(
        production_root=str(resolved_production_root),
        combined_override_root=str(combined_override_root),
        patch_archive_name=patch_result.archive_name,
        patch_archive_staging_dir=patch_result.archive_staging_dir,
        patch_manifest_path=patch_result.manifest_path,
        state_path=str(state_path),
        speaker_count=len(completed_speakers),
        completed_speakers=completed_speakers,
        synced_game_root=synced_game_root,
        notes=[
            "The combined override tree contains every completed speaker's converted OGG files.",
            "The project-level patch-build directory was rebuilt from the combined override tree at the end of the run.",
        ],
    )


def _select_speakers(dataset_root: Path, *, requested_speakers: list[str], min_lines: int) -> list[dict[str, Any]]:
    normalized_targets = {name.casefold() for name in requested_speakers}
    selected: list[dict[str, Any]] = []
    for speaker_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        metadata_path = speaker_dir / "metadata.csv"
        preview_path = speaker_dir / "gptsovits" / "preview_en.csv"
        if not metadata_path.exists() or not preview_path.exists():
            continue

        with metadata_path.open(encoding="utf-8", newline="") as handle:
            metadata_rows = list(csv.DictReader(handle))
        with preview_path.open(encoding="utf-8", newline="") as handle:
            preview_rows = list(csv.DictReader(handle))

        if not metadata_rows or not preview_rows:
            continue

        speaker_name = (metadata_rows[0].get("speaker_name") or speaker_dir.name).strip() or speaker_dir.name
        if normalized_targets and speaker_name.casefold() not in normalized_targets:
            continue

        line_count = len(metadata_rows)
        preview_count = sum(
            1
            for row in preview_rows
            if (row.get("en_text") or "").strip() and Path(row.get("audio_path") or "").exists()
        )
        if line_count < min_lines or preview_count < 1:
            continue

        selected.append(
            {
                "speaker_name": speaker_name,
                "line_count": line_count,
                "preview_count": preview_count,
            }
        )

    selected.sort(key=lambda item: (-int(item["line_count"]), item["speaker_name"]))
    return selected


def _derive_production_name(selected_speakers: list[dict[str, Any]], *, explicit_speakers: list[str]) -> str:
    if not explicit_speakers:
        return "all-cast-v1"

    joined = "|".join(sorted(explicit_speakers))
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:8]
    return f"subset-{digest}-v1"


def _build_run_script(queue_path: Path, *, resolved_repo_root: Path) -> str:
    return f"""$ErrorActionPreference = 'Stop'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = '{resolved_repo_root / "src"}'

$pythonExe = if ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) {{
  Join-Path $env:CONDA_PREFIX 'python.exe'
}} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'))) {{
  Join-Path $env:VIRTUAL_ENV 'Scripts\\python.exe'
}} else {{
  (Get-Command python -ErrorAction Stop).Source
}}

Set-Location '{resolved_repo_root}'
& $pythonExe -s -m duolingal run-gptsovits-production '{queue_path.parent}'
"""


def _build_production_readme(
    *,
    speaker_count: int,
    reference_mode: str,
    inference_limit: int | None,
    sync_game_root: bool,
) -> str:
    limit_text = "全部英文预览句" if inference_limit is None else f"每个角色前 {inference_limit} 句英文预览"
    return (
        "# GPT-SoVITS 夜间量产计划\n\n"
        f"- 角色数：`{speaker_count}`\n"
        f"- 推理范围：`{limit_text}`\n"
        f"- 参考模式：`{reference_mode}`\n"
        f"- 结束后自动同步游戏目录：`{sync_game_root}`\n\n"
        "## 建议用法\n\n"
        "1. 激活 `GPTSoVits` conda 环境\n"
        "2. 保持电脑插电，并关闭会抢 GPU 的程序\n"
        "3. 运行 `scripts/run-production.ps1`\n"
        "4. 产物会持续累积到 `game-ready/unencrypted/`\n"
        "5. 中断后可再次运行，同一角色完成的阶段会尽量跳过\n"
        "6. 起床后先看 `production-status.txt`，能快速知道停在谁、停在哪个阶段\n\n"
        "## 说明\n\n"
        "- 这条队列会顺序执行：前处理 -> GPT -> SoVITS -> 切权重 -> 批量推理 -> 转 OGG\n"
        "- 最终会把所有完成角色的 OGG 合并成一棵总覆盖树\n"
        "- 跑完全队列后，会用这棵总覆盖树重建一次项目级 `patch-build`\n"
        "- 队列运行中会持续更新 `production-state.json` 和 `production-status.txt`\n"
    )


def _load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"completed_speakers": []}
    return json.loads(state_path.read_text(encoding="utf-8"))


def _write_state(
    state_path: Path,
    completed_speakers: list[GptSovitsProductionRunSpeakerStatus],
    *,
    total_speakers: int,
    current_speaker: str | None,
    current_stage: str,
    last_event: str,
    status_path: Path,
) -> None:
    payload = {
        "completed_speakers": [item.model_dump(mode="json", exclude_none=True) for item in completed_speakers],
        "total_speakers": total_speakers,
        "completed_count": len(completed_speakers),
        "current_speaker": current_speaker,
        "current_stage": current_stage,
        "last_event": last_event,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    completed_lines = [
        f"- {item.speaker_name}: generated={item.generated_count}, converted={item.converted_count}"
        for item in completed_speakers[-10:]
    ]
    status_lines = [
        "# GPT-SoVITS Production Status",
        "",
        f"- updated_at: {payload['updated_at']}",
        f"- progress: {payload['completed_count']}/{payload['total_speakers']}",
        f"- current_stage: {current_stage}",
        f"- current_speaker: {current_speaker or '(none)'}",
        f"- last_event: {last_event}",
        "",
        "## Recently Completed Speakers",
    ]
    if completed_lines:
        status_lines.extend(completed_lines)
    else:
        status_lines.append("- (none yet)")
    status_path.write_text("\n".join(status_lines) + "\n", encoding="utf-8", newline="\n")


def _run_powershell_script(script_path: Path, log_path: Path, *, label: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    process = subprocess.Popen(
        command,
        cwd=str(script_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
    )
    assert process.stdout is not None
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        for line in process.stdout:
            print(f"[{label}] {line}", end="")
            handle.write(line)
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {returncode}. See {log_path}")


def _find_gpt_weight(weights_dir: Path, *, experiment_name: str, epoch: int) -> Path | None:
    candidate = weights_dir / f"{experiment_name}-e{epoch}.ckpt"
    return candidate if candidate.exists() else None


def _find_sovits_weight(weights_dir: Path, *, experiment_name: str, epoch: int) -> Path | None:
    matches = sorted(weights_dir.glob(f"{experiment_name}_e{epoch}_s*.pth"))
    if not matches:
        return None
    return matches[-1]


def _api_ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/docs", timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def _start_api_server(plan: dict[str, Any], logs_dir: Path, *, label: str) -> subprocess.Popen[str]:
    gpt_root = Path(plan["gpt_sovits_root"]).resolve()
    python_executable = Path(sys.executable).resolve()
    log_path = logs_dir / f"{label}-api.log"
    handle = log_path.open("a", encoding="utf-8", newline="\n")
    process = subprocess.Popen(
        [
            str(python_executable),
            "-s",
            "api_v2.py",
            "-a",
            "127.0.0.1",
            "-p",
            str(plan["api_port"]),
            "-c",
            "GPT_SoVITS/configs/tts_infer.yaml",
        ],
        cwd=str(gpt_root),
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONNOUSERSITE": "1"},
    )

    deadline = time.time() + 120
    while time.time() < deadline:
        if _api_ready(int(plan["api_port"])):
            return process
        if process.poll() is not None:
            raise RuntimeError(f"GPT-SoVITS api_v2.py exited early. See {log_path}")
        time.sleep(2)

    process.terminate()
    raise RuntimeError(f"Timed out waiting for GPT-SoVITS api_v2.py. See {log_path}")


def _set_weight(port: int, endpoint: str, weight_path: Path) -> None:
    url = f"http://127.0.0.1:{port}/{endpoint}?weights_path={urllib.parse.quote(str(weight_path).replace(os.sep, '/'), safe=':/')}"
    with urllib.request.urlopen(url, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Weight switch failed for {weight_path}: HTTP {response.status}")


def _synthesize_batch(batch_dir: Path, port: int) -> None:
    request_list_path = batch_dir / "requests.jsonl"
    output_dir = batch_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    for line in request_list_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        output_path = output_dir / entry["output_file_name"]
        if output_path.exists():
            continue

        body = json.dumps(entry["request"], ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/tts",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                output_path.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"TTS request failed for {entry['output_file_name']}: {detail}") from exc


def _merge_batch_outputs_into_override(batch_dir: Path, combined_override_root: Path, *, target_sample_rate: int) -> int:
    requests_path = batch_dir / "requests.csv"
    outputs_dir = batch_dir / "outputs"
    with requests_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    converted = 0
    for row in rows:
        source_output_name = (row.get("output_file_name") or "").strip()
        target_voice_file = (row.get("voice_file") or "").strip()
        if not source_output_name or not target_voice_file:
            continue

        source_output_path = outputs_dir / source_output_name
        if not source_output_path.exists():
            raise ValueError(f"Synthesized WAV output does not exist: {source_output_path}")

        destination_path = combined_override_root / target_voice_file
        _convert_wav_to_ogg(source_output_path, destination_path, target_sample_rate=target_sample_rate)
        converted += 1

    return converted


def _sync_game_root(game_root: Path, combined_override_root: Path) -> str:
    target_root = game_root / "unencrypted"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_file in combined_override_root.rglob("*"):
        if not source_file.is_file():
            continue
        relative_path = source_file.relative_to(combined_override_root)
        destination = target_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)
    return str(target_root)
