from __future__ import annotations

import json
import shutil
from pathlib import Path

from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import PatchPreparationResult


def prepare_patch_staging(
    project_root: str | Path,
    source_root: str | Path,
    *,
    archive_name: str | None = None,
) -> PatchPreparationResult:
    manifest = load_project_manifest(project_root)
    resolved_project_root = Path(manifest.workspace_path).resolve()
    resolved_source_root = Path(source_root).expanduser().resolve()
    if not resolved_source_root.exists():
        raise ValueError(f"Override source directory does not exist: {resolved_source_root}")

    if not any(resolved_source_root.rglob("*")):
        raise ValueError(f"Override source directory is empty: {resolved_source_root}")

    resolved_archive_name = archive_name or _default_archive_name(manifest.resource_packages)
    staging_root = resolved_project_root / "patch-build"
    archive_staging_dir = staging_root / resolved_archive_name
    archive_staging_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[str] = []
    for source_file in sorted(resolved_source_root.rglob("*")):
        if not source_file.is_file():
            continue
        relative_path = source_file.relative_to(resolved_source_root)
        destination = archive_staging_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)
        copied_files.append(str(relative_path).replace("\\", "/"))

    if not copied_files:
        raise ValueError(f"No files were copied from: {resolved_source_root}")

    manifest_path = staging_root / f"{resolved_archive_name}.manifest.json"
    pack_script_path = staging_root / f"pack-{resolved_archive_name}.ps1"

    manifest_payload = {
        "archive_name": resolved_archive_name,
        "source_root": str(resolved_source_root),
        "archive_staging_dir": str(archive_staging_dir),
        "copied_files": copied_files,
        "notes": [
            "Copy the archive staging directory into your local game experiment folder before running Xp3Pack.",
            "The generated script looks for Xp3Pack.exe next to itself first, then relies on that local path.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    pack_script_path.write_text(
        _build_pack_script(resolved_archive_name),
        encoding="utf-8",
    )

    return PatchPreparationResult(
        project_root=str(resolved_project_root),
        source_root=str(resolved_source_root),
        archive_name=resolved_archive_name,
        staging_root=str(staging_root),
        archive_staging_dir=str(archive_staging_dir),
        pack_script_path=str(pack_script_path),
        manifest_path=str(manifest_path),
        file_count=len(copied_files),
        copied_files=copied_files,
        notes=[
            "This only prepares the patch staging directory inside the project workspace.",
            "Run Xp3Pack manually in your local game experiment directory after copying the staging folder there.",
        ],
    )


def _default_archive_name(resource_packages: list[str]) -> str:
    normalized = {package.lower() for package in resource_packages}
    if "patch.xp3" in normalized:
        return "patch2"
    return "patch"


def _build_pack_script(archive_name: str) -> str:
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"$archiveName = '{archive_name}'",
            "$tool = Join-Path $PSScriptRoot 'Xp3Pack.exe'",
            "$stagingDir = Join-Path $PSScriptRoot $archiveName",
            "if (-not (Test-Path $stagingDir -PathType Container)) {",
            "  throw \"Archive staging directory not found: $stagingDir\"",
            "}",
            "if (-not (Test-Path $tool -PathType Leaf)) {",
            "  throw \"Xp3Pack.exe was not found: $tool\"",
            "}",
            "& $tool $archiveName",
        ]
    )
