from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from duolingal.config import DEFAULT_PROJECT_SUBDIRS, PROJECTS_ROOT
from duolingal.core.analyzer import sanitize_project_id
from duolingal.domain.models import GameAnalysis, ProjectManifest


def initialize_project_workspace(
    analysis: GameAnalysis,
    project_id: str | None = None,
    projects_root: Path | None = None,
) -> ProjectManifest:
    if not analysis.exists:
        raise ValueError("游戏目录不存在，无法初始化项目。")
    if not analysis.supported or not analysis.game_id or not analysis.engine:
        raise ValueError("当前目录尚未被识别为支持的样本游戏。")

    base_root = projects_root or PROJECTS_ROOT
    base_root.mkdir(parents=True, exist_ok=True)

    resolved_project_id = sanitize_project_id(project_id or analysis.game_id)
    project_root = base_root / resolved_project_id
    project_root.mkdir(parents=True, exist_ok=True)

    for subdir in DEFAULT_PROJECT_SUBDIRS:
        (project_root / subdir).mkdir(parents=True, exist_ok=True)

    manifest = ProjectManifest(
        project_id=resolved_project_id,
        title=analysis.candidate_title or resolved_project_id,
        game_id=analysis.game_id,
        engine=analysis.engine,
        root_path=analysis.root_path,
        workspace_path=str(project_root),
        resource_packages=[package.name for package in analysis.packages],
        resource_package_map={package.name: package.relative_path for package in analysis.packages},
        script_format=analysis.script_format,
        language_support=analysis.text_languages,
        voice_language=analysis.voice_language,
        notes=analysis.notes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    manifest_path = project_root / "project_manifest.json"
    manifest_path.write_text(
        manifest.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    snapshot = {
        "game_root": analysis.root_path,
        "packages": [package.model_dump() for package in analysis.packages],
        "dlls": analysis.dlls,
        "executables": analysis.executables,
        "matched_signatures": analysis.matched_signatures,
    }
    (project_root / "directory_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return manifest


def load_project_manifest(project_root: str | Path) -> ProjectManifest:
    manifest_path = Path(project_root).expanduser().resolve() / "project_manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"未找到项目清单：{manifest_path}")
    return ProjectManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
