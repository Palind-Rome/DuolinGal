from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

try:  # Python 3.11+
    from enum import StrEnum
except ImportError:  # pragma: no cover - compatibility path for Python 3.10 helper envs.
    class StrEnum(str, Enum):
        pass


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolStatus(StrEnum):
    FOUND = "found"
    MISSING = "missing"
    NOT_CHECKED = "not_checked"


class AlignmentStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    MISSING_VOICE = "missing_voice"
    MISSING_ENGLISH = "missing_english"


class ExtractionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DecompileStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PreflightStage(StrEnum):
    EXTRACT = "extract"
    DECOMPILE_SCRIPTS = "decompile_scripts"
    BUILD_LINES = "build_lines"


class PreflightCheckStatus(StrEnum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"


class PackageInfo(BaseModel):
    name: str
    relative_path: str


class GameAnalysis(BaseModel):
    root_path: str
    exists: bool
    game_id: str | None = None
    candidate_title: str | None = None
    engine: str | None = None
    script_format: str | None = None
    voice_language: str | None = None
    text_languages: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    supported: bool = False
    matched_signatures: list[str] = Field(default_factory=list)
    packages: list[PackageInfo] = Field(default_factory=list)
    dlls: list[str] = Field(default_factory=list)
    executables: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ProjectManifest(BaseModel):
    project_id: str
    title: str
    game_id: str
    engine: str
    root_path: str
    workspace_path: str
    primary_executable: str | None = None
    resource_packages: list[str] = Field(default_factory=list)
    resource_package_map: dict[str, str] = Field(default_factory=dict)
    script_format: str | None = None
    language_support: list[str] = Field(default_factory=list)
    voice_language: str | None = None
    notes: list[str] = Field(default_factory=list)
    created_at: str


class ToolRequirement(BaseModel):
    key: str
    display_name: str
    purpose: str
    homepage: str
    integration_mode: Literal["manual", "optional", "planned"] = "manual"
    redistribution_note: str | None = None
    executable_hint: str | None = None
    configured_path: str | None = None
    status: ToolStatus = ToolStatus.NOT_CHECKED
    resolved_command: str | None = None


class ToolConfigEntry(BaseModel):
    path: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class ToolchainConfig(BaseModel):
    source_path: str | None = None
    tools: dict[str, ToolConfigEntry] = Field(default_factory=dict)


class CommandSpec(BaseModel):
    executable: str
    args: list[str] = Field(default_factory=list)
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float | None = None


class CommandResult(BaseModel):
    command: list[str]
    cwd: str | None = None
    returncode: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int


class ExtractionPlan(BaseModel):
    package_name: str
    package_path: str
    output_dir: str
    tool_key: str
    command: list[str]


class ExtractionResult(BaseModel):
    package_name: str
    package_path: str
    output_dir: str
    status: ExtractionStatus
    log_path: str
    run: CommandResult


class ScriptDecompilePlan(BaseModel):
    source_path: str
    output_path: str
    tool_key: str
    command: list[str]


class ScriptDecompileResult(BaseModel):
    source_path: str
    output_path: str
    status: DecompileStatus
    log_path: str
    run: CommandResult


class KrkrDumpPreparationResult(BaseModel):
    project_root: str
    game_executable: str
    loader_path: str
    dll_path: str
    config_path: str
    output_directory: str
    launch_command: str
    backup_config_path: str | None = None
    notes: list[str] = Field(default_factory=list)


class LinesBuildResult(BaseModel):
    project_root: str
    script_root: str
    output_path: str
    nodes_path: str
    scene_count: int
    node_count: int
    line_count: int


class PreflightCheck(BaseModel):
    key: str
    label: str
    status: PreflightCheckStatus
    detail: str
    path: str | None = None


class PreflightReport(BaseModel):
    project_root: str
    config_path: str | None = None
    target_stage: PreflightStage
    overall_status: PreflightCheckStatus
    checks: list[PreflightCheck] = Field(default_factory=list)
    recommended_commands: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    game_path: str


class InitProjectRequest(BaseModel):
    game_path: str
    project_id: str | None = None


class ExtractRequest(BaseModel):
    project_root: str
    config_path: str | None = None
    package_names: list[str] | None = None


class DecompileScriptsRequest(BaseModel):
    project_root: str
    config_path: str | None = None
    input_root: str | None = None
    output_root: str | None = None


class PrepareKrkrDumpRequest(BaseModel):
    project_root: str
    config_path: str | None = None
    output_root: str | None = None


class BuildLinesRequest(BaseModel):
    project_root: str
    script_root: str | None = None


class PreflightRequest(BaseModel):
    project_root: str
    config_path: str | None = None
    target_stage: PreflightStage = PreflightStage.BUILD_LINES


class PreparePocRequest(BaseModel):
    project_root: str
    voice_root: str
    line_id: str | None = None
    speaker_name: str | None = None
    contains: str | None = None


class PreparePatchRequest(BaseModel):
    project_root: str
    source_root: str
    archive_name: str | None = None


class ExportDatasetRequest(BaseModel):
    project_root: str
    voice_root: str
    speaker_name: str | None = None
    min_lines: int = 1


class PrepareGptSovitsRequest(BaseModel):
    project_root: str
    dataset_root: str | None = None
    speaker_name: str | None = None


class PrepareGptSovitsBatchRequest(BaseModel):
    project_root: str
    speaker_name: str
    limit: int = 10
    prompt_line_id: str | None = None
    reference_mode: Literal["anchor", "per-line", "auto"] = "anchor"


class PrepareGptSovitsTrainingRequest(BaseModel):
    project_root: str
    speaker_name: str
    gpt_sovits_root: str | None = None
    version: Literal["v2"] = "v2"
    gpu: str = "0"
    is_half: bool = True
    gpt_epochs: int = 12
    sovits_epochs: int = 6
    gpt_batch_size: int = 4
    sovits_batch_size: int = 4


class RawScriptNode(BaseModel):
    scene_id: str
    order_index: int
    speaker_name: str | None = None
    jp_text: str | None = None
    en_text: str | None = None
    voice_file: str | None = None
    source_path: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AlignedLine(BaseModel):
    line_id: str
    scene_id: str
    order_index: int
    speaker_name: str | None = None
    jp_text: str | None = None
    en_text: str | None = None
    voice_file: str | None = None
    status: AlignmentStatus
    evidence: list[str] = Field(default_factory=list)


class PocPreparationResult(BaseModel):
    project_root: str
    line_id: str
    scene_id: str
    order_index: int
    speaker_name: str | None = None
    jp_text: str | None = None
    en_text: str | None = None
    voice_file: str
    source_voice_path: str
    workspace_dir: str
    original_voice_path: str
    game_ready_voice_path: str
    metadata_path: str
    notes_path: str
    notes: list[str] = Field(default_factory=list)


class PatchPreparationResult(BaseModel):
    project_root: str
    source_root: str
    archive_name: str
    staging_root: str
    archive_staging_dir: str
    pack_script_path: str
    manifest_path: str
    file_count: int
    copied_files: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SpeakerDatasetSummary(BaseModel):
    speaker_name: str
    slug: str
    line_count: int
    output_dir: str
    metadata_path: str


class DatasetExportResult(BaseModel):
    project_root: str
    voice_root: str
    output_root: str
    speaker_count: int
    line_count: int
    speakers: list[SpeakerDatasetSummary] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GptSovitsSpeakerResult(BaseModel):
    speaker_name: str
    output_dir: str
    train_list_path: str
    preview_targets_path: str
    line_count: int


class GptSovitsPreparationResult(BaseModel):
    project_root: str
    dataset_root: str
    speaker_count: int
    line_count: int
    speakers: list[GptSovitsSpeakerResult] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GptSovitsBatchItem(BaseModel):
    line_id: str
    voice_file: str
    source_audio_path: str
    jp_text: str
    en_text: str
    output_file_name: str
    prompt_line_id: str
    prompt_audio_path: str
    prompt_text: str
    prompt_source: Literal["anchor", "self", "anchor-fallback"]


class GptSovitsBatchResult(BaseModel):
    project_root: str
    speaker_name: str
    batch_dir: str
    output_dir: str
    request_list_path: str
    request_table_path: str
    invoke_script_path: str
    reference_mode: Literal["anchor", "per-line", "auto"] = "anchor"
    prompt_line_id: str
    prompt_audio_path: str
    prompt_text: str
    item_count: int
    items: list[GptSovitsBatchItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GptSovitsTrainingPreparationResult(BaseModel):
    project_root: str
    speaker_name: str
    speaker_alias: str
    experiment_name: str
    gpt_sovits_root: str
    training_root: str
    source_audio_root: str
    input_list_path: str
    exp_dir: str
    gpt_config_path: str
    sovits_config_path: str
    prepare_stage1_script_path: str
    prepare_stage2_script_path: str
    prepare_stage3_script_path: str
    prepare_all_script_path: str
    train_gpt_script_path: str
    train_sovits_script_path: str
    train_all_script_path: str
    readme_path: str
    line_count: int
    notes: list[str] = Field(default_factory=list)


class PrepareGptSovitsReinjectRequest(BaseModel):
    project_root: str
    batch_dir: str
    target_voice_file: str
    source_output_name: str | None = None
    target_sample_rate: int = 48000
    archive_name: str | None = None


class GptSovitsReinjectResult(BaseModel):
    project_root: str
    batch_dir: str
    source_output_name: str
    source_output_path: str
    target_voice_file: str
    workspace_dir: str
    override_root: str
    game_ready_voice_path: str
    target_sample_rate: int
    patch_archive_name: str
    patch_staging_root: str
    patch_archive_staging_dir: str
    patch_manifest_path: str
    patch_pack_script_path: str
    notes_path: str
    notes: list[str] = Field(default_factory=list)


class PrepareGptSovitsReinjectBatchRequest(BaseModel):
    project_root: str
    batch_dir: str
    limit: int | None = None
    target_sample_rate: int = 48000
    archive_name: str | None = None


class GptSovitsReinjectBatchItem(BaseModel):
    line_id: str
    target_voice_file: str
    source_output_name: str
    source_output_path: str
    game_ready_voice_path: str
    en_text: str
    prompt_source: Literal["anchor", "self", "anchor-fallback"] | None = None


class GptSovitsReinjectBatchResult(BaseModel):
    project_root: str
    batch_dir: str
    workspace_dir: str
    override_root: str
    target_sample_rate: int
    item_count: int
    items: list[GptSovitsReinjectBatchItem] = Field(default_factory=list)
    patch_archive_name: str
    patch_staging_root: str
    patch_archive_staging_dir: str
    patch_manifest_path: str
    patch_pack_script_path: str
    notes_path: str
    notes: list[str] = Field(default_factory=list)
