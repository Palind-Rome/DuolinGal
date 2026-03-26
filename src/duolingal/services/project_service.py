from __future__ import annotations

from pathlib import Path

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.decompiler import decompile_project_scripts
from duolingal.core.extractor import extract_project_packages
from duolingal.core.krkrdump import prepare_project_krkrdump
from duolingal.core.parser import build_lines_for_project
from duolingal.core.preflight import run_project_preflight
from duolingal.core.tool_config import load_toolchain_config
from duolingal.core.tooling import resolve_tooling_status
from duolingal.core.workspace import initialize_project_workspace
from duolingal.domain.models import (
    ExtractionResult,
    GameAnalysis,
    KrkrDumpPreparationResult,
    LinesBuildResult,
    PreflightReport,
    PreflightStage,
    ProjectManifest,
    ScriptDecompileResult,
    ToolRequirement,
)


class ProjectService:
    def analyze(self, game_path: str | Path) -> GameAnalysis:
        return analyze_game_directory(game_path)

    def init_project(self, game_path: str | Path, project_id: str | None = None) -> ProjectManifest:
        analysis = self.analyze(game_path)
        return initialize_project_workspace(analysis, project_id=project_id)

    def list_tools(self, config_path: str | Path | None = None) -> list[ToolRequirement]:
        config = load_toolchain_config(config_path)
        return resolve_tooling_status(config)

    def extract(
        self,
        project_root: str | Path,
        config_path: str | Path | None = None,
        package_names: list[str] | None = None,
    ) -> list[ExtractionResult]:
        config = load_toolchain_config(config_path)
        return extract_project_packages(project_root, config, package_names=package_names)

    def decompile_scripts(
        self,
        project_root: str | Path,
        config_path: str | Path | None = None,
        input_root: str | Path | None = None,
        output_root: str | Path | None = None,
    ) -> list[ScriptDecompileResult]:
        config = load_toolchain_config(config_path)
        return decompile_project_scripts(
            project_root,
            config,
            input_root=input_root,
            output_root=output_root,
        )

    def prepare_krkrdump(
        self,
        project_root: str | Path,
        config_path: str | Path | None = None,
        output_root: str | Path | None = None,
    ) -> KrkrDumpPreparationResult:
        config = load_toolchain_config(config_path)
        return prepare_project_krkrdump(
            project_root,
            config,
            output_root=output_root,
        )

    def preflight(
        self,
        project_root: str | Path,
        config_path: str | Path | None = None,
        target_stage: PreflightStage = PreflightStage.BUILD_LINES,
    ) -> PreflightReport:
        return run_project_preflight(
            project_root,
            config_path=config_path,
            target_stage=target_stage,
        )

    def build_lines(
        self,
        project_root: str | Path,
        script_root: str | Path | None = None,
    ) -> LinesBuildResult:
        return build_lines_for_project(project_root, script_root=script_root)
