from __future__ import annotations

from shutil import which

from duolingal.domain.models import ToolRequirement, ToolStatus


KNOWN_TOOLS: tuple[ToolRequirement, ...] = (
    ToolRequirement(
        key="krkrextract",
        display_name="KrkrExtract",
        purpose="解包或回包 KiriKiri XP3 资源。",
        homepage="https://github.com/unlimit999/KrkrExtract",
        executable_hint="KrkrExtract.exe",
        integration_mode="manual",
    ),
    ToolRequirement(
        key="freemote",
        display_name="FreeMote",
        purpose="反编译/重建 SCN、PSB、PSB.m 等资源。",
        homepage="https://github.com/UlyssesWu/FreeMote",
        executable_hint="PsbDecompile.exe",
        integration_mode="manual",
        redistribution_note="上游仓库声明使用其代码或二进制发布时需要附带许可证，并包含非商业限制；建议仅作为外部工具接入。",
    ),
    ToolRequirement(
        key="kirikiritools",
        display_name="KirikiriTools",
        purpose="验证 unencrypted.xp3/patch.xp3 覆盖链路与回注流程。",
        homepage="https://github.com/arcusmaximus/KirikiriTools",
        executable_hint="Xp3Pack.exe",
        integration_mode="manual",
    ),
    ToolRequirement(
        key="ffmpeg",
        display_name="FFmpeg",
        purpose="音频裁切、重采样、响度归一与编码转换。",
        homepage="https://ffmpeg.org/",
        executable_hint="ffmpeg.exe",
        integration_mode="manual",
    ),
    ToolRequirement(
        key="gpt-sovits",
        display_name="GPT-SoVITS",
        purpose="角色音色克隆与英文语音合成。",
        homepage="https://github.com/RVC-Boss/GPT-SoVITS",
        executable_hint="api_v2.py",
        integration_mode="planned",
    ),
)


def resolve_tooling_status() -> list[ToolRequirement]:
    resolved: list[ToolRequirement] = []
    for tool in KNOWN_TOOLS:
        command = _resolve_command(tool)
        resolved.append(
            tool.model_copy(
                update={
                    "status": ToolStatus.FOUND if command else ToolStatus.MISSING,
                    "resolved_command": command,
                }
            )
        )
    return resolved


def _resolve_command(tool: ToolRequirement) -> str | None:
    if tool.executable_hint is None:
        return None
    return which(tool.executable_hint)
