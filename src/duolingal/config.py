from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT / "workspace"
PROJECTS_ROOT = WORKSPACE_ROOT / "projects"

DEFAULT_PROJECT_SUBDIRS = (
    "raw_assets",
    "extracted_voice",
    "extracted_script",
    "dataset",
    "models",
    "generated_voice",
    "release",
    "logs",
)
