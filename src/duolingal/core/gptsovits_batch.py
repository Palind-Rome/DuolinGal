from __future__ import annotations

import csv
import json
from pathlib import Path

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import GptSovitsBatchItem, GptSovitsBatchResult


def prepare_gptsovits_batch(
    project_root: str | Path,
    speaker_name: str,
    *,
    limit: int = 10,
    prompt_line_id: str | None = None,
) -> GptSovitsBatchResult:
    if limit < 1:
        raise ValueError("Batch size must be at least 1.")

    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    dataset_root = resolved_project_root / "tts-dataset"
    if not dataset_root.exists():
        raise ValueError(f"TTS dataset root does not exist: {dataset_root}")

    speaker_dir, preview_rows = _find_speaker_preview(dataset_root, speaker_name)
    if not preview_rows:
        raise ValueError(f"No English preview rows found for speaker: {speaker_name}")

    valid_rows = [row for row in preview_rows if (row.get("en_text") or "").strip() and Path(row["audio_path"]).exists()]
    if not valid_rows:
        raise ValueError(f"No valid GPT-SoVITS preview rows found for speaker: {speaker_name}")

    prompt_row = _pick_prompt_row(valid_rows, prompt_line_id)
    target_rows = valid_rows[:limit]

    batch_name = f"first-{len(target_rows):02d}-en"
    batch_dir = speaker_dir / "gptsovits" / "batches" / batch_name
    output_dir = batch_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    request_list_path = batch_dir / "requests.jsonl"
    request_table_path = batch_dir / "requests.csv"
    invoke_script_path = batch_dir / "invoke_api_v2.ps1"
    notes_path = batch_dir / "README.zh-CN.md"

    items: list[GptSovitsBatchItem] = []
    request_rows: list[dict[str, str]] = []
    request_jsonl_lines: list[str] = []

    for index, row in enumerate(target_rows, start=1):
        voice_file = Path(row["audio_path"]).name
        output_file_name = f"{Path(voice_file).stem}.wav"
        output_path = output_dir / output_file_name

        item = GptSovitsBatchItem(
            line_id=row["line_id"],
            voice_file=voice_file,
            source_audio_path=row["audio_path"],
            jp_text=row["jp_text"],
            en_text=row["en_text"],
            output_file_name=output_file_name,
        )
        items.append(item)

        request_rows.append(
            {
                "order_index": str(index),
                "line_id": item.line_id,
                "voice_file": item.voice_file,
                "source_audio_path": item.source_audio_path,
                "jp_text": item.jp_text,
                "en_text": item.en_text,
                "output_file_name": item.output_file_name,
                "output_path": str(output_path),
            }
        )

        request_jsonl_lines.append(
            json.dumps(
                {
                    "line_id": item.line_id,
                    "voice_file": item.voice_file,
                    "output_file_name": item.output_file_name,
                    "source_audio_path": item.source_audio_path,
                    "request": {
                        "text": item.en_text,
                        "text_lang": "en",
                        "ref_audio_path": prompt_row["audio_path"],
                        "prompt_text": prompt_row["jp_text"],
                        "prompt_lang": "ja",
                        "media_type": "wav",
                    },
                },
                ensure_ascii=False,
            )
        )

    request_list_path.write_text("\n".join(request_jsonl_lines) + "\n", encoding="utf-8", newline="\n")
    with request_table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "order_index",
                "line_id",
                "voice_file",
                "source_audio_path",
                "jp_text",
                "en_text",
                "output_file_name",
                "output_path",
            ],
        )
        writer.writeheader()
        for row in request_rows:
            writer.writerow(row)

    invoke_script_path.write_text(
        _build_invoke_script(request_list_path, output_dir),
        encoding="utf-8",
        newline="\n",
    )
    notes_path.write_text(
        _build_notes(
            speaker_name=speaker_name,
            prompt_line_id=prompt_row["line_id"],
            prompt_audio_path=prompt_row["audio_path"],
            prompt_text=prompt_row["jp_text"],
            item_count=len(items),
        ),
        encoding="utf-8",
        newline="\n",
    )

    return GptSovitsBatchResult(
        project_root=str(resolved_project_root),
        speaker_name=speaker_name,
        batch_dir=str(batch_dir),
        output_dir=str(output_dir),
        request_list_path=str(request_list_path),
        request_table_path=str(request_table_path),
        invoke_script_path=str(invoke_script_path),
        prompt_line_id=prompt_row["line_id"],
        prompt_audio_path=prompt_row["audio_path"],
        prompt_text=prompt_row["jp_text"],
        item_count=len(items),
        items=items,
        notes=[
            "requests.jsonl follows the official GPT-SoVITS api_v2 request shape for /tts.",
            "This batch keeps one Japanese reference audio and prompt text, then asks GPT-SoVITS to synthesize English targets.",
            "Outputs are staged as WAV first for debugging. Convert to OGG only after the spoken English passes QA.",
        ],
    )


def _find_speaker_preview(dataset_root: Path, speaker_name: str) -> tuple[Path, list[dict[str, str]]]:
    normalized_target = speaker_name.casefold()
    for speaker_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        preview_path = speaker_dir / "gptsovits" / "preview_en.csv"
        if not preview_path.exists():
            continue

        with preview_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            continue

        current_name = (rows[0].get("speaker_name") or speaker_dir.name).strip() or speaker_dir.name
        if current_name.casefold() == normalized_target:
            return speaker_dir, rows

    raise ValueError(f"GPT-SoVITS preview data was not found for speaker: {speaker_name}")


def _pick_prompt_row(rows: list[dict[str, str]], prompt_line_id: str | None) -> dict[str, str]:
    if prompt_line_id is None:
        return rows[0]

    for row in rows:
        if (row.get("line_id") or "").strip() == prompt_line_id:
            return row

    raise ValueError(f"Prompt line was not found in GPT-SoVITS preview data: {prompt_line_id}")


def _build_invoke_script(request_list_path: Path, output_dir: Path) -> str:
    return f"""param(
  [string]$ApiBase = 'http://127.0.0.1:9880'
)

$ErrorActionPreference = 'Stop'

$requestList = Join-Path $PSScriptRoot '{request_list_path.name}'
$outputDir = Join-Path $PSScriptRoot '{output_dir.name}'

if (-not (Test-Path $requestList -PathType Leaf)) {{
  throw "Request list not found: $requestList"
}}

if (-not (Test-Path $outputDir -PathType Container)) {{
  New-Item -ItemType Directory -Path $outputDir | Out-Null
}}

Get-Content $requestList -Encoding UTF8 | ForEach-Object {{
  if (-not $_.Trim()) {{
    return
  }}

  $entry = $_ | ConvertFrom-Json
  $body = $entry.request | ConvertTo-Json -Depth 8
  $outputPath = Join-Path $outputDir $entry.output_file_name

  Invoke-WebRequest `
    -Uri ($ApiBase.TrimEnd('/') + '/tts') `
    -Method Post `
    -ContentType 'application/json; charset=utf-8' `
    -Body $body `
    -OutFile $outputPath | Out-Null

  Write-Host "Generated $($entry.output_file_name)"
}}
"""


def _build_notes(
    *,
    speaker_name: str,
    prompt_line_id: str,
    prompt_audio_path: str,
    prompt_text: str,
    item_count: int,
) -> str:
    return (
        "# GPT-SoVITS 英文合成批次\n\n"
        f"- 角色：`{speaker_name}`\n"
        f"- 条目数：`{item_count}`\n"
        f"- 参考台词 line_id：`{prompt_line_id}`\n"
        f"- 参考音频：`{prompt_audio_path}`\n"
        f"- 参考日文：`{prompt_text}`\n\n"
        "## 用法\n\n"
        "1. 先按 GPT-SoVITS 官方 README 启动 `api_v2.py`\n"
        "2. 在当前目录运行 `invoke_api_v2.ps1`\n"
        "3. 生成结果会写到 `outputs/`\n"
        "4. 先听 WAV，确认英文自然度通过，再决定是否转成 OGG 回灌游戏\n"
    )
