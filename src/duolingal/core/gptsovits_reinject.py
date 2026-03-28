from __future__ import annotations

import csv
from pathlib import Path

from duolingal.core.patching import prepare_patch_staging
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import GptSovitsReinjectResult


def prepare_gptsovits_reinject(
    project_root: str | Path,
    batch_dir: str | Path,
    *,
    target_voice_file: str,
    source_output_name: str | None = None,
    target_sample_rate: int = 48000,
    archive_name: str | None = None,
) -> GptSovitsReinjectResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    resolved_batch_dir = Path(batch_dir).expanduser().resolve()
    if not resolved_batch_dir.exists():
        raise ValueError(f"GPT-SoVITS batch directory does not exist: {resolved_batch_dir}")

    outputs_dir = resolved_batch_dir / "outputs"
    if not outputs_dir.exists():
        raise ValueError(f"GPT-SoVITS outputs directory does not exist: {outputs_dir}")

    request_table_path = resolved_batch_dir / "requests.csv"
    if not request_table_path.exists():
        raise ValueError(f"GPT-SoVITS request table does not exist: {request_table_path}")

    rows = _load_request_rows(request_table_path)
    if not rows:
        raise ValueError(f"GPT-SoVITS request table is empty: {request_table_path}")

    selected_row = _pick_row(rows, source_output_name=source_output_name)
    resolved_source_output_name = selected_row["output_file_name"]
    source_output_path = outputs_dir / resolved_source_output_name
    if not source_output_path.exists():
        raise ValueError(f"Synthesized WAV output does not exist: {source_output_path}")

    workspace_dir = resolved_project_root / "poc" / f"gptsovits-{Path(target_voice_file).stem}"
    override_root = workspace_dir / "game-ready" / "unencrypted"
    game_ready_voice_path = override_root / target_voice_file
    override_root.mkdir(parents=True, exist_ok=True)

    _convert_wav_to_ogg(
        source_output_path,
        game_ready_voice_path,
        target_sample_rate=target_sample_rate,
    )

    patch_result = prepare_patch_staging(
        resolved_project_root,
        override_root,
        archive_name=archive_name,
    )

    notes_path = workspace_dir / "README.zh-CN.md"
    notes_path.write_text(
        _build_notes(
            target_voice_file=target_voice_file,
            source_output_name=resolved_source_output_name,
            line_id=selected_row.get("line_id", ""),
            en_text=selected_row.get("en_text", ""),
            target_sample_rate=target_sample_rate,
        ),
        encoding="utf-8",
        newline="\n",
    )

    return GptSovitsReinjectResult(
        project_root=str(resolved_project_root),
        batch_dir=str(resolved_batch_dir),
        source_output_name=resolved_source_output_name,
        source_output_path=str(source_output_path),
        target_voice_file=target_voice_file,
        workspace_dir=str(workspace_dir),
        override_root=str(override_root),
        game_ready_voice_path=str(game_ready_voice_path),
        target_sample_rate=target_sample_rate,
        patch_archive_name=patch_result.archive_name,
        patch_staging_root=patch_result.staging_root,
        patch_archive_staging_dir=patch_result.archive_staging_dir,
        patch_manifest_path=patch_result.manifest_path,
        patch_pack_script_path=patch_result.pack_script_path,
        notes_path=str(notes_path),
        notes=[
            "This step converts one synthesized WAV into a game-ready OGG override file.",
            "A patch staging directory is prepared automatically from the same override tree.",
            "Use unencrypted first for the fastest validation, then pack patch2.xp3 after QA.",
        ],
    )


def _load_request_rows(request_table_path: Path) -> list[dict[str, str]]:
    with request_table_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pick_row(rows: list[dict[str, str]], *, source_output_name: str | None) -> dict[str, str]:
    if source_output_name is None:
        return rows[0]

    normalized_target = source_output_name.strip()
    for row in rows:
        if (row.get("output_file_name") or "").strip() == normalized_target:
            return row

    raise ValueError(f"Requested synthesized output was not found in requests.csv: {source_output_name}")


def _convert_wav_to_ogg(source_output_path: Path, destination_path: Path, *, target_sample_rate: int) -> None:
    try:
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample_poly
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-specific dependency path.
        raise ValueError(
            "WAV->OGG conversion requires `soundfile` and `scipy`. Use a Python environment that has them installed."
        ) from exc

    audio, sample_rate = sf.read(source_output_path, always_2d=False)
    audio_array = np.asarray(audio, dtype=np.float32)

    if audio_array.ndim > 1:
        audio_array = audio_array.mean(axis=1)

    if sample_rate != target_sample_rate:
        audio_array = resample_poly(audio_array, target_sample_rate, sample_rate).astype(np.float32)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination_path, audio_array, target_sample_rate, format="OGG", subtype="VORBIS")


def _build_notes(
    *,
    target_voice_file: str,
    source_output_name: str,
    line_id: str,
    en_text: str,
    target_sample_rate: int,
) -> str:
    return (
        "# GPT-SoVITS 自动回灌准备\n\n"
        f"- 来源输出：`{source_output_name}`\n"
        f"- 对应 line_id：`{line_id}`\n"
        f"- 英文文本：`{en_text}`\n"
        f"- 目标游戏文件名：`{target_voice_file}`\n"
        f"- 转换目标：`{target_sample_rate} Hz / 单声道 / Ogg Vorbis`\n\n"
        "## 说明\n\n"
        "1. 这个目录里的 `game-ready/unencrypted` 可直接用于快速覆盖测试\n"
        "2. 同时已经自动准备好了 `patch-build` 下的补丁 staging\n"
        "3. 先验证游戏里能播，再决定是否批量打包成 `patch2.xp3`\n"
    )
