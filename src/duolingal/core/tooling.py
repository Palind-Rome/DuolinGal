from __future__ import annotations

from pathlib import Path
from shutil import which

from duolingal.core.tool_config import ToolchainConfig
from duolingal.domain.models import ToolRequirement, ToolStatus


KNOWN_TOOLS: tuple[ToolRequirement, ...] = (
    ToolRequirement(
        key="krkrdump",
        display_name="KrkrDump",
        purpose="Prepare a runtime dump config for Kirikiri Z script assets.",
        homepage="https://github.com/crskycode/KrkrDump",
        executable_hint="KrkrDumpLoader.exe",
        integration_mode="manual",
    ),
    ToolRequirement(
        key="krkrextract",
        display_name="KrkrExtract",
        purpose="Offline unpack or repack KiriKiri XP3 archives when CLI support is available.",
        homepage="https://github.com/xmoezzz/KrkrExtract",
        executable_hint="KrkrExtract.exe",
        integration_mode="optional",
    ),
    ToolRequirement(
        key="freemote",
        display_name="FreeMote",
        purpose="Decompile and rebuild SCN, PSB, and PSB.m assets.",
        homepage="https://github.com/UlyssesWu/FreeMote",
        executable_hint="PsbDecompile.exe",
        integration_mode="manual",
        redistribution_note=(
            "Treat FreeMote as an external dependency. Upstream release notes mention "
            "licensing and plugin deployment constraints."
        ),
    ),
    ToolRequirement(
        key="kirikiritools",
        display_name="KirikiriTools",
        purpose="Validate unencrypted.xp3 and patch.xp3 replacement workflows.",
        homepage="https://github.com/arcusmaximus/KirikiriTools",
        executable_hint="Xp3Pack.exe",
        integration_mode="manual",
    ),
    ToolRequirement(
        key="ffmpeg",
        display_name="FFmpeg",
        purpose="Trim, resample, normalize, and transcode audio files.",
        homepage="https://ffmpeg.org/",
        executable_hint="ffmpeg.exe",
        integration_mode="manual",
    ),
    ToolRequirement(
        key="gpt-sovits",
        display_name="GPT-SoVITS",
        purpose="Clone character voices and synthesize English speech.",
        homepage="https://github.com/RVC-Boss/GPT-SoVITS",
        executable_hint="api_v2.py",
        integration_mode="planned",
    ),
)


def resolve_tooling_status(config: ToolchainConfig | None = None) -> list[ToolRequirement]:
    toolchain_config = config or ToolchainConfig()
    resolved: list[ToolRequirement] = []
    for tool in KNOWN_TOOLS:
        configured_path = _configured_path(toolchain_config, tool.key)
        command = configured_path or _resolve_command(tool)
        status = _resolve_status(tool, command)
        resolved.append(
            tool.model_copy(
                update={
                    "configured_path": configured_path,
                    "status": status,
                    "resolved_command": command,
                }
            )
        )
    return resolved


def _resolve_command(tool: ToolRequirement) -> str | None:
    if tool.executable_hint is None:
        return None
    return which(tool.executable_hint)


def _configured_path(config: ToolchainConfig, tool_key: str) -> str | None:
    entry = config.tools.get(tool_key)
    if entry is None:
        return None
    candidate = Path(entry.path).expanduser().resolve()
    if candidate.exists():
        return str(candidate)
    return None


def _resolve_status(tool: ToolRequirement, command: str | None) -> ToolStatus:
    if command:
        return ToolStatus.FOUND
    if tool.integration_mode == "planned":
        return ToolStatus.NOT_CHECKED
    return ToolStatus.MISSING
