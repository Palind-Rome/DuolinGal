from __future__ import annotations

import csv
from pathlib import Path

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import GptSovitsPreparationResult, GptSovitsSpeakerResult


def prepare_gptsovits_inputs(
    project_root: str | Path,
    dataset_root: str | Path | None = None,
    *,
    speaker_name: str | None = None,
) -> GptSovitsPreparationResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    resolved_dataset_root = (
        Path(dataset_root).expanduser().resolve()
        if dataset_root is not None
        else (resolved_project_root / "tts-dataset").resolve()
    )
    if not resolved_dataset_root.exists():
        raise ValueError(f"Dataset root does not exist: {resolved_dataset_root}")

    normalized_target_speaker = speaker_name.casefold() if speaker_name else None
    speaker_results: list[GptSovitsSpeakerResult] = []
    total_lines = 0

    for speaker_dir in sorted(path for path in resolved_dataset_root.iterdir() if path.is_dir()):
        metadata_path = speaker_dir / "metadata.csv"
        if not metadata_path.exists():
            continue

        rows = _load_rows(metadata_path)
        if not rows:
            continue

        current_speaker_name = (rows[0].get("speaker_name") or speaker_dir.name).strip() or speaker_dir.name
        if normalized_target_speaker and current_speaker_name.casefold() != normalized_target_speaker:
            continue

        gptsovits_dir = speaker_dir / "gptsovits"
        gptsovits_dir.mkdir(parents=True, exist_ok=True)
        train_list_path = gptsovits_dir / "train_ja.list"
        preview_targets_path = gptsovits_dir / "preview_en.csv"

        prepared_rows = []
        for row in rows:
            audio_path = speaker_dir / (row.get("audio_path") or "")
            jp_text = (row.get("jp_text") or "").strip()
            if not audio_path.exists() or not jp_text:
                continue
            prepared_rows.append(
                {
                    "audio_path": str(audio_path.resolve()),
                    "speaker_name": current_speaker_name,
                    "jp_text": jp_text,
                    "en_text": (row.get("en_text") or "").strip(),
                    "line_id": row.get("line_id") or "",
                }
            )

        if not prepared_rows:
            continue

        with train_list_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in prepared_rows:
                handle.write(f"{row['audio_path']}|{row['speaker_name']}|ja|{row['jp_text']}\n")

        with preview_targets_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["line_id", "speaker_name", "jp_text", "en_text", "audio_path"],
            )
            writer.writeheader()
            for row in prepared_rows:
                writer.writerow(
                    {
                        "line_id": row["line_id"],
                        "speaker_name": row["speaker_name"],
                        "jp_text": row["jp_text"],
                        "en_text": row["en_text"],
                        "audio_path": row["audio_path"],
                    }
                )

        speaker_results.append(
            GptSovitsSpeakerResult(
                speaker_name=current_speaker_name,
                output_dir=str(gptsovits_dir),
                train_list_path=str(train_list_path),
                preview_targets_path=str(preview_targets_path),
                line_count=len(prepared_rows),
            )
        )
        total_lines += len(prepared_rows)

    if not speaker_results:
        raise ValueError("No GPT-SoVITS speaker dataset matched the current filters.")

    return GptSovitsPreparationResult(
        project_root=str(resolved_project_root),
        dataset_root=str(resolved_dataset_root),
        speaker_count=len(speaker_results),
        line_count=total_lines,
        speakers=speaker_results,
        notes=[
            "train_ja.list follows the official GPT-SoVITS text list format: vocal_path|speaker_name|language|text.",
            "preview_en.csv keeps the paired English lines so later synthesis and QA can reuse the same mapping.",
            "This preparation step does not resample, normalize, or trim the original galgame audio.",
        ],
    )


def _load_rows(metadata_path: Path) -> list[dict[str, str]]:
    with metadata_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
