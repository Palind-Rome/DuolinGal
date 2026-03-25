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
    status: ToolStatus = ToolStatus.NOT_CHECKED
    resolved_command: str | None = None


class AnalyzeRequest(BaseModel):
    game_path: str


class InitProjectRequest(BaseModel):
    game_path: str
    project_id: str | None = None


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
