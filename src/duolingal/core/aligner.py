from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from duolingal.domain.models import AlignedLine, AlignmentStatus, RawScriptNode


def build_alignment_stub(nodes: Iterable[RawScriptNode]) -> list[AlignedLine]:
    aligned: list[AlignedLine] = []
    for node in nodes:
        status = _infer_status(node)
        evidence: list[str] = []
        if node.voice_file:
            evidence.append("voice_file")
        if node.en_text:
            evidence.append("en_text")
        if node.speaker_name:
            evidence.append("speaker_name")
        if node.jp_text:
            evidence.append("jp_text")

        aligned.append(
            AlignedLine(
                line_id=f"{node.scene_id}-{node.order_index:04d}",
                scene_id=node.scene_id,
                order_index=node.order_index,
                speaker_name=node.speaker_name,
                jp_text=node.jp_text,
                en_text=node.en_text,
                voice_file=node.voice_file,
                status=status,
                evidence=evidence,
            )
        )
    return aligned


def export_alignment_csv(lines: Iterable[AlignedLine], destination: str | Path) -> Path:
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "line_id",
                "scene_id",
                "order_index",
                "speaker_name",
                "voice_file",
                "jp_text",
                "en_text",
                "status",
                "evidence",
            ],
        )
        writer.writeheader()
        for line in lines:
            writer.writerow(
                {
                    "line_id": line.line_id,
                    "scene_id": line.scene_id,
                    "order_index": line.order_index,
                    "speaker_name": line.speaker_name,
                    "voice_file": line.voice_file,
                    "jp_text": line.jp_text,
                    "en_text": line.en_text,
                    "status": line.status,
                    "evidence": "|".join(line.evidence),
                }
            )
    return output_path


def _infer_status(node: RawScriptNode) -> AlignmentStatus:
    if not node.voice_file:
        return AlignmentStatus.MISSING_VOICE
    if not node.en_text:
        return AlignmentStatus.MISSING_ENGLISH
    if not node.speaker_name:
        return AlignmentStatus.NEEDS_REVIEW
    return AlignmentStatus.READY
