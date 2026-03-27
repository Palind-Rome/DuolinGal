from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from duolingal.domain.models import PocPreparationResult
from duolingal.core.workspace import load_project_manifest


def prepare_single_line_poc(
    project_root: str | Path,
    voice_root: str | Path,
    *,
    line_id: str | None = None,
    speaker_name: str | None = None,
    contains: str | None = None,
) -> PocPreparationResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    resolved_voice_root = Path(voice_root).expanduser().resolve()

    if not resolved_voice_root.exists():
        raise ValueError(f"Voice directory does not exist: {resolved_voice_root}")

    lines_path = resolved_project_root / "dataset" / "lines.csv"
    if not lines_path.exists():
        raise ValueError(f"lines.csv does not exist yet: {lines_path}")

    rows = _load_lines(lines_path)
    candidate = _select_candidate(
        rows,
        resolved_voice_root,
        line_id=line_id,
        speaker_name=speaker_name,
        contains=contains,
    )
    if candidate is None:
        raise ValueError("No ready voice line matched the current filters.")

    voice_file = candidate["voice_file"]
    source_voice_path = resolved_voice_root / voice_file
    if not source_voice_path.exists():
        raise ValueError(f"Voice file was selected but does not exist: {source_voice_path}")

    poc_root = resolved_project_root / "poc" / _sanitize_for_path(candidate["line_id"])
    original_dir = poc_root / "original"
    game_ready_dir = poc_root / "game-ready" / "unencrypted"
    original_dir.mkdir(parents=True, exist_ok=True)
    game_ready_dir.mkdir(parents=True, exist_ok=True)

    original_voice_path = original_dir / voice_file
    game_ready_voice_path = game_ready_dir / voice_file
    shutil.copy2(source_voice_path, original_voice_path)
    shutil.copy2(source_voice_path, game_ready_voice_path)

    metadata_path = poc_root / "metadata.json"
    notes_path = poc_root / "README.zh-CN.md"

    metadata = {
        "line_id": candidate["line_id"],
        "scene_id": candidate["scene_id"],
        "order_index": int(candidate["order_index"]),
        "speaker_name": candidate.get("speaker_name") or None,
        "voice_file": voice_file,
        "source_voice_path": str(source_voice_path),
        "original_voice_path": str(original_voice_path),
        "game_ready_voice_path": str(game_ready_voice_path),
        "jp_text": candidate.get("jp_text") or None,
        "en_text": candidate.get("en_text") or None,
        "status": candidate.get("status"),
        "evidence": candidate.get("evidence"),
        "notes": [
            "The original extracted voice has been copied into both original/ and game-ready/unencrypted/.",
            "Replace the file in game-ready/unencrypted/ with your generated English voice before testing.",
            "Use version.dll and extract-unencrypted.txt only in a local experiment directory, not in the tracked repository.",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    notes_path.write_text(
        _build_notes(
            line_id=candidate["line_id"],
            speaker_name=candidate.get("speaker_name") or "",
            voice_file=voice_file,
            jp_text=candidate.get("jp_text") or "",
            en_text=candidate.get("en_text") or "",
        ),
        encoding="utf-8",
    )

    return PocPreparationResult(
        project_root=str(resolved_project_root),
        line_id=candidate["line_id"],
        scene_id=candidate["scene_id"],
        order_index=int(candidate["order_index"]),
        speaker_name=candidate.get("speaker_name") or None,
        jp_text=candidate.get("jp_text") or None,
        en_text=candidate.get("en_text") or None,
        voice_file=voice_file,
        source_voice_path=str(source_voice_path),
        workspace_dir=str(poc_root),
        original_voice_path=str(original_voice_path),
        game_ready_voice_path=str(game_ready_voice_path),
        metadata_path=str(metadata_path),
        notes_path=str(notes_path),
        notes=[
            "This PoC stays on the all-ages path and does not touch adult.xp3 or adult2.xp3.",
            "The generated game-ready/unencrypted directory mirrors the override layout expected by KirikiriTools version.dll.",
        ],
    )


def _load_lines(lines_path: Path) -> list[dict[str, str]]:
    with lines_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _select_candidate(
    rows: list[dict[str, str]],
    voice_root: Path,
    *,
    line_id: str | None,
    speaker_name: str | None,
    contains: str | None,
) -> dict[str, str] | None:
    normalized_speaker = speaker_name.casefold() if speaker_name else None
    normalized_contains = contains.casefold() if contains else None

    candidates: list[dict[str, str]] = []
    for row in rows:
        if row.get("status") != "ready":
            continue

        voice_file = row.get("voice_file") or ""
        if not voice_file or not (voice_root / voice_file).exists():
            continue

        if line_id and row.get("line_id") != line_id:
            continue

        row_speaker = row.get("speaker_name") or ""
        if normalized_speaker and row_speaker.casefold() != normalized_speaker:
            continue

        if normalized_contains:
            jp_text = row.get("jp_text") or ""
            en_text = row.get("en_text") or ""
            haystack = "\n".join((row_speaker, jp_text, en_text)).casefold()
            if normalized_contains not in haystack:
                continue

        candidates.append(row)

    if not candidates:
        return None

    candidates.sort(key=_candidate_sort_key)
    return candidates[0]


def _candidate_sort_key(row: dict[str, str]) -> tuple[Any, ...]:
    english = row.get("en_text") or ""
    speaker = row.get("speaker_name") or ""
    voice = row.get("voice_file") or ""
    jp_text = row.get("jp_text") or ""

    return (
        0 if speaker else 1,
        0 if 8 <= len(english) <= 72 else 1,
        0 if english and not english.endswith("...") else 1,
        len(english),
        len(jp_text),
        voice,
        row.get("line_id") or "",
    )


def _build_notes(
    *,
    line_id: str,
    speaker_name: str,
    voice_file: str,
    jp_text: str,
    en_text: str,
) -> str:
    return "\n".join(
        [
            "# Single-line PoC",
            "",
            f"- `line_id`: `{line_id}`",
            f"- `speaker`: `{speaker_name}`" if speaker_name else "- `speaker`: narrator / unknown",
            f"- `voice_file`: `{voice_file}`",
            f"- `jp_text`: `{jp_text}`",
            f"- `en_text`: `{en_text}`",
            "",
            "## What to do next",
            "",
            "1. Replace the copied file under `game-ready/unencrypted/` with your generated English `.ogg`.",
            "2. In your local game experiment directory, install `version.dll` from KirikiriTools.",
            "3. Put the resulting `unencrypted/` override tree next to the game executable.",
            "4. Run the game and jump to this line to confirm the replacement is heard.",
            "",
            "This PoC intentionally stays on the all-ages path.",
        ]
    )


def _sanitize_for_path(value: str) -> str:
    allowed = []
    for character in value:
        if character.isalnum() or character in {"-", "_", "."}:
            allowed.append(character)
        else:
            allowed.append("_")
    sanitized = "".join(allowed).strip("._")
    return sanitized or "line"
