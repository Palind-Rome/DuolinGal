from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


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


class BuildLinesRequest(BaseModel):
    project_root: str
    script_root: str | None = None


class PreflightRequest(BaseModel):
    project_root: str
    config_path: str | None = None
    target_stage: PreflightStage = PreflightStage.BUILD_LINES


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
