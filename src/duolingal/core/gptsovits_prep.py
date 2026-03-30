from __future__ import annotations

import csv
import json
from pathlib import Path

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import GptSovitsPreparationResult, GptSovitsSpeakerResult


_PREVIEW_TARGETS = (
    ("en", "preview_en.csv", "en_text"),
    ("zh-cn", "preview_cn.csv", "cn_text"),
    ("zh-tw", "preview_tw.csv", "tw_text"),
)


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
    translations_by_line_id = _load_translation_lookup(resolved_project_root)

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
        preview_target_paths = {
            target_language: str((gptsovits_dir / file_name).resolve())
            for target_language, file_name, _ in _PREVIEW_TARGETS
        }

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
                    "cn_text": (row.get("cn_text") or translations_by_line_id.get(row.get("line_id") or "", {}).get("cn_text") or "").strip(),
                    "tw_text": (row.get("tw_text") or translations_by_line_id.get(row.get("line_id") or "", {}).get("tw_text") or "").strip(),
                    "line_id": row.get("line_id") or "",
                }
            )

        if not prepared_rows:
            continue

        with train_list_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in prepared_rows:
                handle.write(f"{row['audio_path']}|{row['speaker_name']}|ja|{row['jp_text']}\n")

        for target_language, file_name, text_key in _PREVIEW_TARGETS:
            preview_targets_path = gptsovits_dir / file_name
            with preview_targets_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "line_id",
                        "speaker_name",
                        "jp_text",
                        "target_language",
                        "target_text",
                        "en_text",
                        "cn_text",
                        "tw_text",
                        "audio_path",
                    ],
                )
                writer.writeheader()
                for row in prepared_rows:
                    writer.writerow(
                        {
                            "line_id": row["line_id"],
                            "speaker_name": row["speaker_name"],
                            "jp_text": row["jp_text"],
                            "target_language": target_language,
                            "target_text": row[text_key],
                            "en_text": row["en_text"],
                            "cn_text": row["cn_text"],
                            "tw_text": row["tw_text"],
                            "audio_path": row["audio_path"],
                        }
                    )

        speaker_results.append(
            GptSovitsSpeakerResult(
                speaker_name=current_speaker_name,
                output_dir=str(gptsovits_dir),
                train_list_path=str(train_list_path),
                preview_targets_path=preview_target_paths["en"],
                preview_target_paths=preview_target_paths,
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
            "preview_en.csv / preview_cn.csv / preview_tw.csv keep the paired target lines so later synthesis and QA can reuse the same mapping.",
            "This preparation step does not resample, normalize, or trim the original galgame audio.",
        ],
    )


def _load_rows(metadata_path: Path) -> list[dict[str, str]]:
    with metadata_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_translation_lookup(project_root: Path) -> dict[str, dict[str, str]]:
    nodes_path = project_root / "dataset" / "script_nodes.jsonl"
    if not nodes_path.exists():
        return {}

    lookup: dict[str, dict[str, str]] = {}
    with nodes_path.open(encoding="utf-8", newline="\n") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            scene_id = str(payload.get("scene_id") or "").strip()
            order_index = payload.get("order_index")
            if not scene_id or order_index is None:
                continue

            try:
                order_index_int = int(order_index)
            except (TypeError, ValueError):
                continue

            metadata = payload.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}

            cn_text = str(metadata.get("cn_text") or "").strip()
            tw_text = str(metadata.get("tw_text") or "").strip()
            if not cn_text and not tw_text:
                continue

            line_id = f"{scene_id}-{order_index_int:04d}"
            lookup[line_id] = {
                "cn_text": cn_text,
                "tw_text": tw_text,
            }

    return lookup
