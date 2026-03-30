from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

from duolingal.config import REPO_ROOT
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import FinalCleanupCandidateItem, FinalCleanupPreparationResult

_INTERJECTION_WORDS = {
    "ah",
    "aha",
    "eh",
    "er",
    "erm",
    "gah",
    "gee",
    "grr",
    "grrr",
    "ha",
    "hah",
    "heh",
    "hm",
    "hmph",
    "hmm",
    "huh",
    "mm",
    "mmm",
    "mph",
    "ngh",
    "oh",
    "oof",
    "ugh",
    "uh",
    "um",
    "wah",
    "woof",
    "arf",
    "growl",
}
_WEAK_JP_RE = re.compile(r"^[ぁ-んァ-ヶーっッ゛゜!?！？…。、～〜・「」『』（）()\-—―\s]+$")
_NON_ALPHA_RE = re.compile(r"[^A-Za-z0-9]+")
_TEMP_NAME_RE = re.compile(r"^\.(?:gptsovits-ogg-|tmp-)")


def prepare_final_cleanup(
    project_root: str | Path,
    *,
    production_name: str = "all-cast-v1",
    cleanup_name: str = "final-cleanup-v1",
) -> FinalCleanupPreparationResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    production_root = resolved_project_root / "tts-production" / production_name
    production_state_path = production_root / "production-state.json"
    combined_override_root = production_root / "game-ready" / "unencrypted"
    if not production_state_path.exists():
        raise ValueError(f"Production state file does not exist: {production_state_path}")
    if not combined_override_root.exists():
        raise ValueError(f"Combined override root does not exist: {combined_override_root}")

    cleanup_root = resolved_project_root / "tts-release" / cleanup_name
    source_root = cleanup_root / "source" / "unencrypted"
    review_root = cleanup_root / "review"
    scripts_root = cleanup_root / "scripts"
    review_root.mkdir(parents=True, exist_ok=True)
    scripts_root.mkdir(parents=True, exist_ok=True)

    if source_root.exists():
        shutil.rmtree(source_root)
    source_root.parent.mkdir(parents=True, exist_ok=True)
    copied_file_count = _copy_override_tree(combined_override_root, source_root)

    state = json.loads(production_state_path.read_text(encoding="utf-8"))
    candidates = _collect_candidates(state)

    candidates_path = review_root / "weak-utterance-candidates.csv"
    review_sheet_path = review_root / "cleanup-review.csv"
    _write_candidates_csv(candidates_path, candidates, include_review_columns=False)
    _write_candidates_csv(review_sheet_path, candidates, include_review_columns=True)

    apply_script_path = scripts_root / "apply-reviewed-removals.ps1"
    rebuild_patch_script_path = scripts_root / "rebuild-patch-from-clean-copy.ps1"
    readme_path = cleanup_root / "README.zh-CN.md"

    apply_script_path.write_text(_build_apply_script(cleanup_root), encoding="utf-8", newline="\n")
    rebuild_patch_script_path.write_text(
        _build_rebuild_patch_script(cleanup_root, REPO_ROOT),
        encoding="utf-8",
        newline="\n",
    )
    readme_path.write_text(
        _build_cleanup_readme(
            candidate_count=len(candidates),
            copied_file_count=copied_file_count,
            source_root=source_root,
        ),
        encoding="utf-8",
        newline="\n",
    )

    return FinalCleanupPreparationResult(
        project_root=str(resolved_project_root),
        production_root=str(production_root),
        cleanup_root=str(cleanup_root),
        source_override_root=str(source_root),
        review_candidates_path=str(candidates_path),
        review_sheet_path=str(review_sheet_path),
        apply_script_path=str(apply_script_path),
        rebuild_patch_script_path=str(rebuild_patch_script_path),
        readme_path=str(readme_path),
        copied_file_count=copied_file_count,
        candidate_count=len(candidates),
        candidates=candidates,
        notes=[
            "The original production output was not modified.",
            "Review cleanup-review.csv and only mark rows as remove after listening checks.",
            "apply-reviewed-removals.ps1 only touches the copied cleanup source tree.",
        ],
    )


def _copy_override_tree(source_root: Path, destination_root: Path) -> int:
    copied = 0
    for source_path in source_root.rglob("*"):
        relative = source_path.relative_to(source_root)
        if any(_TEMP_NAME_RE.match(part) for part in relative.parts):
            continue
        target_path = destination_root / relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied += 1
    return copied


def _collect_candidates(state: dict[str, object]) -> list[FinalCleanupCandidateItem]:
    candidates: list[FinalCleanupCandidateItem] = []
    completed = state.get("completed_speakers", [])
    if not isinstance(completed, list):
        return candidates

    for speaker_status in completed:
        if not isinstance(speaker_status, dict):
            continue
        speaker_name = str(speaker_status.get("speaker_name", "")).strip()
        batch_dir = Path(str(speaker_status.get("batch_dir", "")).strip())
        requests_csv = batch_dir / "requests.csv"
        if not requests_csv.exists():
            continue
        with requests_csv.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                voice_file = (row.get("voice_file") or "").strip()
                if not voice_file:
                    continue
                reasons = _classify_candidate(
                    en_text=(row.get("en_text") or "").strip(),
                    jp_text=(row.get("jp_text") or "").strip(),
                )
                if not reasons:
                    continue
                candidates.append(
                    FinalCleanupCandidateItem(
                        speaker_name=speaker_name,
                        line_id=(row.get("line_id") or "").strip(),
                        voice_file=voice_file,
                        en_text=(row.get("en_text") or "").strip(),
                        jp_text=(row.get("jp_text") or "").strip(),
                        reason_codes=reasons,
                        suggested_action="review",
                    )
                )
    candidates.sort(key=lambda item: (item.speaker_name, item.voice_file))
    return candidates


def _classify_candidate(*, en_text: str, jp_text: str) -> list[str]:
    reasons: list[str] = []

    normalized_en = en_text.strip()
    if normalized_en and not any(char.isalnum() for char in normalized_en):
        reasons.append("english_punctuation_only")

    english_words = [token.casefold() for token in _NON_ALPHA_RE.split(normalized_en) if token]
    if english_words and len(english_words) <= 2 and all(token in _INTERJECTION_WORDS for token in english_words):
        reasons.append("english_interjection_only")

    normalized_jp = jp_text.strip()
    jp_compact = re.sub(r"[!?！？…。、～〜・「」『』（）()\-—―\s]", "", normalized_jp)
    if normalized_jp and len(jp_compact) <= 2 and _WEAK_JP_RE.fullmatch(normalized_jp):
        reasons.append("jp_short_reaction")

    return list(dict.fromkeys(reasons))


def _write_candidates_csv(path: Path, candidates: list[FinalCleanupCandidateItem], *, include_review_columns: bool) -> None:
    fieldnames = [
        "speaker_name",
        "line_id",
        "voice_file",
        "en_text",
        "jp_text",
        "reason_codes",
        "suggested_action",
    ]
    if include_review_columns:
        fieldnames.extend(["final_action", "review_notes"])

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in candidates:
            row = {
                "speaker_name": item.speaker_name,
                "line_id": item.line_id,
                "voice_file": item.voice_file,
                "en_text": item.en_text,
                "jp_text": item.jp_text,
                "reason_codes": "|".join(item.reason_codes),
                "suggested_action": item.suggested_action,
            }
            if include_review_columns:
                row["final_action"] = ""
                row["review_notes"] = ""
            writer.writerow(row)


def _build_apply_script(cleanup_root: Path) -> str:
    cleanup_root_text = str(cleanup_root)
    return f"""$ErrorActionPreference = 'Stop'
$cleanupRoot = '{cleanup_root_text}'
$reviewSheet = Join-Path $cleanupRoot 'review\\cleanup-review.csv'
$sourceRoot = Join-Path $cleanupRoot 'source\\unencrypted'

if (-not (Test-Path $reviewSheet)) {{
  throw "Review sheet not found: $reviewSheet"
}}

Import-Csv -Path $reviewSheet -Encoding UTF8 | ForEach-Object {{
  $action = ($_.'final_action' | ForEach-Object {{ $_.Trim().ToLowerInvariant() }})
  if ($action -ne 'remove') {{
    return
  }}

  $voiceFile = $_.'voice_file'
  if (-not $voiceFile) {{
    return
  }}

  $targetPath = Join-Path $sourceRoot $voiceFile
  if (Test-Path $targetPath) {{
    Remove-Item -LiteralPath $targetPath -Force
    Write-Host "Removed $voiceFile from cleanup copy"
  }}
}}
"""


def _build_rebuild_patch_script(cleanup_root: Path, repo_root: Path) -> str:
    cleanup_root_text = str(cleanup_root)
    repo_root_text = str(repo_root)
    return f"""$ErrorActionPreference = 'Stop'
$cleanupRoot = '{cleanup_root_text}'
$repoRoot = '{repo_root_text}'
$sourceRoot = Join-Path $cleanupRoot 'source\\unencrypted'
$projectRoot = Split-Path (Split-Path $cleanupRoot -Parent) -Parent

Set-Location $repoRoot
$env:PYTHONPATH = 'src'
python -m duolingal prepare-patch $projectRoot $sourceRoot --archive-name patch2
"""


def _build_cleanup_readme(*, candidate_count: int, copied_file_count: int, source_root: Path) -> str:
    return f"""# 最终清理工作区

这个目录是为“最终弱句 / 纯语气句清理”准备的**安全副本**。

当前状态：

- 已复制文件数：`{copied_file_count}`
- 疑似弱句候选数：`{candidate_count}`
- 工作副本目录：`{source_root.name}`

## 你现在可以做什么

1. 试听 `review/cleanup-review.csv` 中列出的候选句
2. 只在确认该句应保留原音时，把 `final_action` 填成 `remove`
3. 运行：
   - `scripts/apply-reviewed-removals.ps1`
4. 确认清理后的副本没有误删
5. 再运行：
   - `scripts/rebuild-patch-from-clean-copy.ps1`

## 安全说明

- 这里的删除脚本**只会作用于这个副本**
- 原始量产目录不会被改动
- 如果规则判断不准，随时可以删掉这个目录重新准备一次
"""
