from __future__ import annotations

import csv
import shutil
from collections import defaultdict
from pathlib import Path

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import DatasetExportResult, SpeakerDatasetSummary


def export_tts_dataset(
    project_root: str | Path,
    voice_root: str | Path,
    *,
    speaker_name: str | None = None,
    min_lines: int = 1,
) -> DatasetExportResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    resolved_voice_root = Path(voice_root).expanduser().resolve()
    if not resolved_voice_root.exists():
        raise ValueError(f"Voice directory does not exist: {resolved_voice_root}")

    lines_path = resolved_project_root / "dataset" / "lines.csv"
    if not lines_path.exists():
        raise ValueError(f"lines.csv does not exist yet: {lines_path}")

    rows = _load_rows(lines_path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    normalized_target_speaker = speaker_name.casefold() if speaker_name else None

    for row in rows:
        current_speaker = (row.get("speaker_name") or "").strip()
        voice_file = (row.get("voice_file") or "").strip()
        jp_text = (row.get("jp_text") or "").strip()
        if not current_speaker or not voice_file or not jp_text:
            continue

        if normalized_target_speaker and current_speaker.casefold() != normalized_target_speaker:
            continue

        voice_path = resolved_voice_root / voice_file
        if not voice_path.exists():
            continue

        grouped[current_speaker].append(row)

    output_root = resolved_project_root / "tts-dataset"
    output_root.mkdir(parents=True, exist_ok=True)

    speaker_summaries: list[SpeakerDatasetSummary] = []
    total_lines = 0
    for current_speaker in sorted(grouped):
        entries = grouped[current_speaker]
        if len(entries) < min_lines:
            continue

        slug = _slugify_speaker(current_speaker)
        speaker_root = output_root / slug
        audio_dir = speaker_root / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = speaker_root / "metadata.csv"

        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "line_id",
                    "scene_id",
                    "order_index",
                    "speaker_name",
                    "voice_file",
                    "audio_path",
                    "jp_text",
                    "en_text",
                ],
            )
            writer.writeheader()
            for row in entries:
                voice_file = row["voice_file"]
                source_path = resolved_voice_root / voice_file
                destination_path = audio_dir / voice_file
                if not destination_path.exists():
                    shutil.copy2(source_path, destination_path)
                writer.writerow(
                    {
                        "line_id": row["line_id"],
                        "scene_id": row["scene_id"],
                        "order_index": row["order_index"],
                        "speaker_name": current_speaker,
                        "voice_file": voice_file,
                        "audio_path": f"audio/{voice_file}",
                        "jp_text": row["jp_text"],
                        "en_text": row.get("en_text") or "",
                    }
                )

        speaker_summaries.append(
            SpeakerDatasetSummary(
                speaker_name=current_speaker,
                slug=slug,
                line_count=len(entries),
                output_dir=str(speaker_root),
                metadata_path=str(metadata_path),
            )
        )
        total_lines += len(entries)

    if not speaker_summaries:
        raise ValueError("No speaker dataset matched the current filters.")

    return DatasetExportResult(
        project_root=str(resolved_project_root),
        voice_root=str(resolved_voice_root),
        output_root=str(output_root),
        speaker_count=len(speaker_summaries),
        line_count=total_lines,
        speakers=speaker_summaries,
        notes=[
            "This export only uses lines that have speaker_name, jp_text, and a matching voice file.",
            "The current export stays on the all-ages voice path and only uses the provided voice_root.",
        ],
    )


def _load_rows(lines_path: Path) -> list[dict[str, str]]:
    with lines_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _slugify_speaker(speaker_name: str) -> str:
    allowed = []
    for character in speaker_name:
        if character.isalnum():
            allowed.append(character.lower())
        elif character in {"-", "_", "."}:
            allowed.append(character)
        else:
            allowed.append("_")
    slug = "".join(allowed).strip("._")
    return slug or "speaker"
