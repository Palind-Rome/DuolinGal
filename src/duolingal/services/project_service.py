from __future__ import annotations

from pathlib import Path

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.tool_config import load_toolchain_config
from duolingal.core.tooling import resolve_tooling_status
from duolingal.core.workspace import initialize_project_workspace
from duolingal.domain.models import GameAnalysis, ProjectManifest, ToolRequirement


class ProjectService:
    def analyze(self, game_path: str | Path) -> GameAnalysis:
        return analyze_game_directory(game_path)

    def init_project(self, game_path: str | Path, project_id: str | None = None) -> ProjectManifest:
        analysis = self.analyze(game_path)
        return initialize_project_workspace(analysis, project_id=project_id)

    def list_tools(self, config_path: str | Path | None = None) -> list[ToolRequirement]:
        config = load_toolchain_config(config_path)
        return resolve_tooling_status(config)
