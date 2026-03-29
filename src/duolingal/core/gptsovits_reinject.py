from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from duolingal.core.patching import prepare_patch_staging
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import (
    GptSovitsReinjectBatchItem,
    GptSovitsReinjectBatchResult,
    GptSovitsReinjectResult,
)


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


def prepare_gptsovits_reinject_batch(
    project_root: str | Path,
    batch_dir: str | Path,
    *,
    limit: int | None = None,
    target_sample_rate: int = 48000,
    archive_name: str | None = None,
) -> GptSovitsReinjectBatchResult:
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

    selected_rows = rows[:limit] if limit is not None else rows
    if not selected_rows:
        raise ValueError("No GPT-SoVITS rows were selected for batch reinject.")

    workspace_dir = resolved_project_root / "poc" / f"gptsovits-{resolved_batch_dir.name}"
    override_root = workspace_dir / "game-ready" / "unencrypted"
    override_root.mkdir(parents=True, exist_ok=True)

    converted_items: list[GptSovitsReinjectBatchItem] = []
    missing_outputs: list[str] = []
    for row in selected_rows:
        target_voice_file = (row.get("voice_file") or "").strip()
        if not target_voice_file:
            raise ValueError(f"requests.csv row is missing voice_file: {row}")

        source_output_name = (row.get("output_file_name") or "").strip()
        if not source_output_name:
            raise ValueError(f"requests.csv row is missing output_file_name: {row}")

        source_output_path = outputs_dir / source_output_name
        if not source_output_path.exists():
            missing_outputs.append(str(source_output_path))
            continue

        game_ready_voice_path = override_root / target_voice_file
        _convert_wav_to_ogg(
            source_output_path,
            game_ready_voice_path,
            target_sample_rate=target_sample_rate,
        )
        converted_items.append(
            GptSovitsReinjectBatchItem(
                line_id=(row.get("line_id") or "").strip(),
                target_voice_file=target_voice_file,
                source_output_name=source_output_name,
                source_output_path=str(source_output_path),
                game_ready_voice_path=str(game_ready_voice_path),
                en_text=(row.get("en_text") or "").strip(),
                prompt_source=(row.get("prompt_source") or "").strip() or None,
            )
        )

    if missing_outputs:
        preview = "\n".join(missing_outputs[:5])
        suffix = "" if len(missing_outputs) <= 5 else f"\n... and {len(missing_outputs) - 5} more"
        raise ValueError(f"Synthesized WAV outputs are missing:\n{preview}{suffix}")

    if not converted_items:
        raise ValueError("No synthesized WAV outputs were converted for batch reinject.")

    patch_result = prepare_patch_staging(
        resolved_project_root,
        override_root,
        archive_name=archive_name,
    )

    notes_path = workspace_dir / "README.zh-CN.md"
    notes_path.write_text(
        _build_batch_notes(
            batch_name=resolved_batch_dir.name,
            item_count=len(converted_items),
            target_sample_rate=target_sample_rate,
        ),
        encoding="utf-8",
        newline="\n",
    )

    return GptSovitsReinjectBatchResult(
        project_root=str(resolved_project_root),
        batch_dir=str(resolved_batch_dir),
        workspace_dir=str(workspace_dir),
        override_root=str(override_root),
        target_sample_rate=target_sample_rate,
        item_count=len(converted_items),
        items=converted_items,
        patch_archive_name=patch_result.archive_name,
        patch_staging_root=patch_result.staging_root,
        patch_archive_staging_dir=patch_result.archive_staging_dir,
        patch_manifest_path=patch_result.manifest_path,
        patch_pack_script_path=patch_result.pack_script_path,
        notes_path=str(notes_path),
        notes=[
            "This step converts multiple synthesized WAV files into a game-ready OGG override tree.",
            "A clean patch staging directory is rebuilt automatically from the same override tree.",
            "Copy game-ready/unencrypted into the game root for the fastest validation pass.",
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
    if _requires_ascii_staging(source_output_path, destination_path):
        staging_root = _pick_ascii_staging_root(source_output_path, destination_path)
        temp_root = staging_root / f".gptsovits-ogg-{uuid.uuid4().hex}"
        temp_root.mkdir(parents=True, exist_ok=False)
        try:
            staged_source = temp_root / "input.wav"
            staged_destination = temp_root / "output.ogg"
            shutil.copy2(source_output_path, staged_source)
            _convert_wav_to_ogg_impl(staged_source, staged_destination, target_sample_rate=target_sample_rate)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_destination, destination_path)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
        return

    _convert_wav_to_ogg_impl(source_output_path, destination_path, target_sample_rate=target_sample_rate)


def _convert_wav_to_ogg_impl(source_output_path: Path, destination_path: Path, *, target_sample_rate: int) -> None:
    ffmpeg_executable = _resolve_ffmpeg_executable()
    if ffmpeg_executable is not None:
        _convert_wav_to_ogg_with_ffmpeg(
            source_output_path,
            destination_path,
            target_sample_rate=target_sample_rate,
            ffmpeg_executable=ffmpeg_executable,
        )
        return

    try:
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample_poly
    except (ModuleNotFoundError, OSError) as exc:  # pragma: no cover - environment-specific dependency path.
        raise ValueError(
            "WAV->OGG conversion requires a reachable ffmpeg.exe, or soundfile+scipy as a fallback."
        ) from exc

    try:
        audio, sample_rate = sf.read(source_output_path, always_2d=False)
        audio_array = np.asarray(audio, dtype=np.float32)

        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)

        if sample_rate != target_sample_rate:
            audio_array = resample_poly(audio_array, target_sample_rate, sample_rate).astype(np.float32)

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(destination_path, audio_array, target_sample_rate, format="OGG", subtype="VORBIS")
        return
    except Exception as exc:
        raise ValueError("WAV->OGG conversion failed via soundfile/scipy fallback.") from exc


def _convert_wav_to_ogg_with_ffmpeg(
    source_output_path: Path,
    destination_path: Path,
    *,
    target_sample_rate: int,
    ffmpeg_executable: Path | None,
) -> None:
    if ffmpeg_executable is None:
        raise ValueError("WAV->OGG conversion requires `soundfile` and `scipy`, or a reachable ffmpeg.exe.")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(ffmpeg_executable),
            "-y",
            "-i",
            str(source_output_path),
            "-ac",
            "1",
            "-ar",
            str(target_sample_rate),
            "-c:a",
            "libvorbis",
            str(destination_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or "Unknown ffmpeg failure."
        raise ValueError(f"WAV->OGG conversion failed via ffmpeg: {error_text}")


def _requires_ascii_staging(*paths: Path) -> bool:
    for path in paths:
        try:
            str(path).encode("ascii")
        except UnicodeEncodeError:
            return True
    return False


def _pick_ascii_staging_root(source_output_path: Path, destination_path: Path) -> Path:
    candidates = [
        destination_path.parent,
        Path.cwd(),
        Path(tempfile.gettempdir()),
        source_output_path.parent,
    ]
    for candidate in candidates:
        try:
            str(candidate).encode("ascii")
        except UnicodeEncodeError:
            continue
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    return destination_path.parent


def _resolve_ffmpeg_executable() -> Path | None:
    candidate = shutil.which("ffmpeg")
    if candidate:
        return Path(candidate).resolve()

    env_root = Path(sys.executable).resolve().parent.parent
    for base in (Path(sys.prefix), env_root):
        ffmpeg_path = base / "Library" / "bin" / "ffmpeg.exe"
        if ffmpeg_path.exists():
            return ffmpeg_path.resolve()

    return None


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


def _build_batch_notes(
    *,
    batch_name: str,
    item_count: int,
    target_sample_rate: int,
) -> str:
    return (
        "# GPT-SoVITS 批量回灌准备\n\n"
        f"- 批次目录：`{batch_name}`\n"
        f"- 已转换条目：`{item_count}`\n"
        f"- 转换目标：`{target_sample_rate} Hz / 单声道 / Ogg Vorbis`\n\n"
        "## 说明\n\n"
        "1. 这个目录里的 `game-ready/unencrypted` 是可直接复制进游戏目录的批量覆盖树\n"
        "2. 同时已经自动重建好了 `patch-build` 下的补丁 staging\n"
        "3. 建议先用 `unencrypted` 快速体验，再决定是否打包成 `patch2.xp3`\n"
    )
