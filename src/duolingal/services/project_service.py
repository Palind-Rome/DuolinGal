from __future__ import annotations

from pathlib import Path

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.dataset_export import export_tts_dataset
from duolingal.core.gptsovits_batch import prepare_gptsovits_batch as prepare_gptsovits_batch_inputs
from duolingal.core.decompiler import decompile_project_scripts
from duolingal.core.extractor import extract_project_packages
from duolingal.core.gptsovits_prep import prepare_gptsovits_inputs
from duolingal.core.krkrdump import prepare_project_krkrdump
from duolingal.core.parser import build_lines_for_project
from duolingal.core.patching import prepare_patch_staging
from duolingal.core.poc import prepare_single_line_poc
from duolingal.core.preflight import run_project_preflight
from duolingal.core.tool_config import load_toolchain_config
from duolingal.core.tooling import resolve_tooling_status
from duolingal.core.workspace import initialize_project_workspace
from duolingal.domain.models import (
    DatasetExportResult,
    GptSovitsBatchResult,
    ExtractionResult,
    GameAnalysis,
    GptSovitsPreparationResult,
    KrkrDumpPreparationResult,
    LinesBuildResult,
    PatchPreparationResult,
    PocPreparationResult,
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

    def prepare_poc(
        self,
        project_root: str | Path,
        voice_root: str | Path,
        *,
        line_id: str | None = None,
        speaker_name: str | None = None,
        contains: str | None = None,
    ) -> PocPreparationResult:
        return prepare_single_line_poc(
            project_root,
            voice_root,
            line_id=line_id,
            speaker_name=speaker_name,
            contains=contains,
        )

    def prepare_patch(
        self,
        project_root: str | Path,
        source_root: str | Path,
        *,
        archive_name: str | None = None,
    ) -> PatchPreparationResult:
        return prepare_patch_staging(
            project_root,
            source_root,
            archive_name=archive_name,
        )

    def export_dataset(
        self,
        project_root: str | Path,
        voice_root: str | Path,
        *,
        speaker_name: str | None = None,
        min_lines: int = 1,
    ) -> DatasetExportResult:
        return export_tts_dataset(
            project_root,
            voice_root,
            speaker_name=speaker_name,
            min_lines=min_lines,
        )

    def prepare_gptsovits(
        self,
        project_root: str | Path,
        dataset_root: str | Path | None = None,
        *,
        speaker_name: str | None = None,
    ) -> GptSovitsPreparationResult:
        return prepare_gptsovits_inputs(
            project_root,
            dataset_root=dataset_root,
            speaker_name=speaker_name,
        )

    def prepare_gptsovits_batch(
        self,
        project_root: str | Path,
        speaker_name: str,
        *,
        limit: int = 10,
        prompt_line_id: str | None = None,
    ) -> GptSovitsBatchResult:
        return prepare_gptsovits_batch_inputs(
            project_root,
            speaker_name,
            limit=limit,
            prompt_line_id=prompt_line_id,
        )
