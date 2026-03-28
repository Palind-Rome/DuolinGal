from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path
from typing import Literal

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import GptSovitsBatchItem, GptSovitsBatchResult

ReferenceMode = Literal["anchor", "per-line", "auto"]
PromptSource = Literal["anchor", "self", "anchor-fallback"]

_REFERENCE_MODES: set[str] = {"anchor", "per-line", "auto"}
_PROMPT_STRIP_RE = re.compile(r"[「」『』（）()\[\]【】〈〉《》〔〕…—ー・,，、。！？!?.~〜\-　\s]")
_KANA_ONLY_RE = re.compile(r"[ぁ-ゖァ-ヺー]+")
_REFERENCE_MIN_SECONDS = 3.0
_REFERENCE_MAX_SECONDS = 10.0


def prepare_gptsovits_batch(
    project_root: str | Path,
    speaker_name: str,
    *,
    limit: int = 10,
    prompt_line_id: str | None = None,
    reference_mode: ReferenceMode = "anchor",
) -> GptSovitsBatchResult:
    if limit < 1:
        raise ValueError("Batch size must be at least 1.")
    if reference_mode not in _REFERENCE_MODES:
        raise ValueError(f"Unsupported GPT-SoVITS reference mode: {reference_mode}")

    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    dataset_root = resolved_project_root / "tts-dataset"
    if not dataset_root.exists():
        raise ValueError(f"TTS dataset root does not exist: {dataset_root}")

    speaker_dir, preview_rows = _find_speaker_preview(dataset_root, speaker_name)
    if not preview_rows:
        raise ValueError(f"No English preview rows found for speaker: {speaker_name}")

    valid_rows = [
        row
        for row in preview_rows
        if _has_meaningful_target_text(row.get("en_text") or "") and Path(row["audio_path"]).exists()
    ]
    if not valid_rows:
        raise ValueError(f"No valid GPT-SoVITS preview rows found for speaker: {speaker_name}")

    anchor_row = _pick_prompt_row(valid_rows, prompt_line_id)
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
    anchor_fallback_count = 0

    for index, row in enumerate(target_rows, start=1):
        prompt_row, prompt_source = _select_prompt_row(
            target_row=row,
            anchor_row=anchor_row,
            reference_mode=reference_mode,
        )
        if prompt_source == "anchor-fallback":
            anchor_fallback_count += 1

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
            prompt_line_id=prompt_row["line_id"],
            prompt_audio_path=prompt_row["audio_path"],
            prompt_text=prompt_row["jp_text"],
            prompt_source=prompt_source,
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
                "prompt_line_id": item.prompt_line_id,
                "prompt_audio_path": item.prompt_audio_path,
                "prompt_text": item.prompt_text,
                "prompt_source": item.prompt_source,
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
                        "ref_audio_path": item.prompt_audio_path,
                        "prompt_text": item.prompt_text,
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
                "prompt_line_id",
                "prompt_audio_path",
                "prompt_text",
                "prompt_source",
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
            reference_mode=reference_mode,
            anchor_line_id=anchor_row["line_id"],
            anchor_audio_path=anchor_row["audio_path"],
            anchor_text=anchor_row["jp_text"],
            item_count=len(items),
            anchor_fallback_count=anchor_fallback_count,
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
        reference_mode=reference_mode,
        prompt_line_id=anchor_row["line_id"],
        prompt_audio_path=anchor_row["audio_path"],
        prompt_text=anchor_row["jp_text"],
        item_count=len(items),
        items=items,
        notes=[
            "requests.jsonl follows the official GPT-SoVITS api_v2 request shape for /tts.",
            "reference_mode=anchor keeps one Japanese reference line for the whole batch.",
            "reference_mode=per-line uses each row's own JP text and audio as the GPT-SoVITS prompt.",
            "reference_mode=auto prefers per-line prompts, but falls back to the anchor prompt for very short, interjection-like, or 3~10-second-invalid reference lines.",
            "Preview rows whose English target collapses to punctuation-only text are skipped before batch synthesis.",
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


def _select_prompt_row(
    *,
    target_row: dict[str, str],
    anchor_row: dict[str, str],
    reference_mode: ReferenceMode,
) -> tuple[dict[str, str], PromptSource]:
    if reference_mode == "anchor":
        return anchor_row, "anchor"
    if reference_mode == "per-line":
        return target_row, "self"
    if _looks_weak_as_prompt(target_row.get("jp_text") or ""):
        return anchor_row, "anchor-fallback"

    prompt_duration = _probe_audio_duration_seconds(target_row.get("audio_path") or "")
    if prompt_duration is not None and not (_REFERENCE_MIN_SECONDS <= prompt_duration <= _REFERENCE_MAX_SECONDS):
        return anchor_row, "anchor-fallback"

    return target_row, "self"


def _looks_weak_as_prompt(text: str) -> bool:
    core_text = _PROMPT_STRIP_RE.sub("", text)
    if len(core_text) < 3:
        return True
    if len(core_text) <= 5 and _KANA_ONLY_RE.fullmatch(core_text):
        return True
    return False


def _has_meaningful_target_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return any(char.isalnum() for char in stripped)


def _probe_audio_duration_seconds(audio_path: str) -> float | None:
    path = Path(audio_path)
    if not path.exists():
        return None

    for probe in (_probe_with_soundfile, _probe_with_audioread, _probe_with_ffprobe):
        duration = probe(path)
        if duration is not None:
            return duration
    return None


def _probe_with_soundfile(path: Path) -> float | None:
    try:
        import soundfile  # type: ignore
    except Exception:
        return None

    try:
        return float(soundfile.info(str(path)).duration)
    except Exception:
        return None


def _probe_with_audioread(path: Path) -> float | None:
    try:
        import audioread  # type: ignore
    except Exception:
        return None

    try:
        with audioread.audio_open(str(path)) as handle:
            return float(handle.duration)
    except Exception:
        return None


def _probe_with_ffprobe(path: Path) -> float | None:
    commands = (
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        ["ffmpeg", "-i", str(path)],
    )

    for command in commands:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        if command[0] == "ffprobe":
            output = (completed.stdout or "").strip()
            try:
                return float(output)
            except ValueError:
                continue

        duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stderr or "")
        if duration_match:
            hours = int(duration_match.group(1))
            minutes = int(duration_match.group(2))
            seconds = float(duration_match.group(3))
            return hours * 3600 + minutes * 60 + seconds

    return None


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
    reference_mode: ReferenceMode,
    anchor_line_id: str,
    anchor_audio_path: str,
    anchor_text: str,
    item_count: int,
    anchor_fallback_count: int,
) -> str:
    mode_lines = {
        "anchor": "整批固定使用一条参考句，最稳，但跨句语气恢复有限。",
        "per-line": "每句都使用自己的日语参考句和参考音频，更容易带回原句语气。",
        "auto": "优先每句自带参考；如果日语参考太短、太像语气词，或参考音频不在 3~10 秒内，再回退到锚点参考句。",
    }
    return (
        "# GPT-SoVITS 英文合成批次\n\n"
        f"- 角色：`{speaker_name}`\n"
        f"- 条目数：`{item_count}`\n"
        f"- 参考模式：`{reference_mode}`\n"
        f"- 锚点 line_id：`{anchor_line_id}`\n"
        f"- 锚点音频：`{anchor_audio_path}`\n"
        f"- 锚点日文：`{anchor_text}`\n"
        f"- auto 回退次数：`{anchor_fallback_count}`\n\n"
        f"{mode_lines[reference_mode]}\n\n"
        "## 用法\n\n"
        "1. 先按 GPT-SoVITS 官方 README 启动 `api_v2.py`\n"
        "2. 在当前目录运行 `invoke_api_v2.ps1`\n"
        "3. 生成结果会写到 `outputs/`\n"
        "4. 先听 WAV，确认英文自然度通过，再决定是否转成 OGG 回灌游戏\n\n"
        "## 什么时候不适合强行每句自带参考\n\n"
        "- 如果某句日文几乎只有语气词，比如 `えっ`、`うむ`、`……`，它能提供的韵律上下文很弱\n"
        f"- 如果参考音频时长不在 `{_REFERENCE_MIN_SECONDS:.0f}~{_REFERENCE_MAX_SECONDS:.0f}` 秒内，GPT-SoVITS `api_v2.py` 也会直接拒绝\n"
        "- 即使已经训练出角色基座音色，参考句仍然会影响当前句子的停顿、情绪和落点\n"
        "- 所以 `auto` 往往比无脑 `per-line` 更稳，尤其适合中途试听和批量首轮 QA\n"
    )
