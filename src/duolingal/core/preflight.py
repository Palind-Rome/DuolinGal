from __future__ import annotations

from pathlib import Path

from duolingal.core.tool_config import ToolchainConfig, load_toolchain_config
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import (
    PreflightCheck,
    PreflightCheckStatus,
    PreflightReport,
    PreflightStage,
    ProjectManifest,
)


def run_project_preflight(
    project_root: str | Path,
    config_path: str | Path | None = None,
    target_stage: PreflightStage = PreflightStage.BUILD_LINES,
) -> PreflightReport:
    manifest = load_project_manifest(project_root)
    config = load_toolchain_config(config_path)
    resolved_project_root = Path(manifest.workspace_path).resolve()

    checks = _build_checks(manifest, config, target_stage)
    overall_status = _summarize_checks(checks)
    recommended_commands = _recommend_commands(
        project_root=resolved_project_root,
        config_path=config.source_path,
        check_map={check.key: check for check in checks},
        target_stage=target_stage,
    )

    return PreflightReport(
        project_root=str(resolved_project_root),
        config_path=config.source_path,
        target_stage=target_stage,
        overall_status=overall_status,
        checks=checks,
        recommended_commands=recommended_commands,
    )


def _build_checks(
    manifest: ProjectManifest,
    config: ToolchainConfig,
    target_stage: PreflightStage,
) -> list[PreflightCheck]:
    project_root = Path(manifest.workspace_path).resolve()
    game_root = Path(manifest.root_path).resolve()
    extracted_script_root = project_root / "extracted_script"
    decompiled_script_root = project_root / "decompiled_script"

    extracted_script_assets = _count_script_assets(extracted_script_root)
    extracted_json_files = _count_json_files(extracted_script_root)
    decompiled_json_files = _count_json_files(decompiled_script_root)
    json_ready_for_build_lines = decompiled_json_files > 0 or extracted_json_files > 0

    checks: list[PreflightCheck] = [
        _make_check(
            key="game_root",
            label="游戏目录",
            status=_status_for_requirement(game_root.exists(), required=target_stage == PreflightStage.EXTRACT),
            detail="已找到游戏安装目录。" if game_root.exists() else "游戏安装目录不存在。",
            path=game_root,
        ),
        _check_resource_package(
            manifest,
            game_root,
            "voice.xp3",
            required=target_stage == PreflightStage.EXTRACT,
        ),
        _check_resource_package(
            manifest,
            game_root,
            "scn.xp3",
            required=target_stage == PreflightStage.EXTRACT,
        ),
        _check_tool(
            config,
            tool_key="krkrextract",
            label="KrkrExtract",
            required_placeholders=("{package}", "{output}"),
            required=target_stage == PreflightStage.EXTRACT,
        ),
    ]

    freemote_required = target_stage == PreflightStage.DECOMPILE_SCRIPTS or (
        target_stage == PreflightStage.BUILD_LINES and not json_ready_for_build_lines
    )
    extracted_assets_required = target_stage == PreflightStage.DECOMPILE_SCRIPTS or (
        target_stage == PreflightStage.BUILD_LINES and not json_ready_for_build_lines
    )

    checks.extend(
        [
            _make_check(
                key="extracted_script_dir",
                label="提取脚本目录",
                status=_status_for_requirement(extracted_script_root.exists(), required=extracted_assets_required),
                detail=(
                    f"已找到提取脚本目录，包含 {extracted_script_assets} 个候选脚本文件。"
                    if extracted_script_root.exists()
                    else "未找到 extracted_script 目录。"
                ),
                path=extracted_script_root,
            ),
            _make_check(
                key="extracted_script_assets",
                label="候选脚本文件",
                status=_status_for_requirement(extracted_script_assets > 0, required=extracted_assets_required),
                detail=(
                    f"发现 {extracted_script_assets} 个 .scn/.psb/.psb.m 文件。"
                    if extracted_script_assets > 0
                    else "还没有可反编译的 .scn/.psb/.psb.m 文件。"
                ),
                path=extracted_script_root,
            ),
            _check_tool(
                config,
                tool_key="freemote",
                label="FreeMote",
                required_placeholders=("{input}", "{output}"),
                required=freemote_required,
            ),
        ]
    )

    checks.extend(
        [
            _make_check(
                key="decompiled_script_json",
                label="反编译 JSON",
                status=_status_for_requirement(decompiled_json_files > 0, required=False),
                detail=(
                    f"发现 {decompiled_json_files} 个反编译 JSON。"
                    if decompiled_json_files > 0
                    else "decompiled_script 中还没有 JSON。"
                ),
                path=decompiled_script_root,
            ),
            _make_check(
                key="json_sources_for_build_lines",
                label="可解析 JSON 输入",
                status=_status_for_requirement(
                    json_ready_for_build_lines,
                    required=target_stage == PreflightStage.BUILD_LINES,
                ),
                detail=(
                    f"当前可用于 build-lines 的 JSON 总数为 {decompiled_json_files + extracted_json_files}。"
                    if json_ready_for_build_lines
                    else "还没有可供 build-lines 使用的 JSON。"
                ),
                path=decompiled_script_root if decompiled_json_files > 0 else extracted_script_root,
            ),
        ]
    )

    return checks


def _check_tool(
    config: ToolchainConfig,
    tool_key: str,
    label: str,
    required_placeholders: tuple[str, ...],
    required: bool,
) -> PreflightCheck:
    entry = config.tools.get(tool_key)
    if entry is None:
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="工具未在配置文件中声明。",
        )

    executable = Path(entry.path).expanduser().resolve()
    if not executable.exists():
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="配置中的工具路径不存在。",
            path=executable,
        )

    if not entry.args:
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="工具缺少 args 模板。",
            path=executable,
        )

    joined_args = " ".join(entry.args)
    missing_placeholders = [placeholder for placeholder in required_placeholders if placeholder not in joined_args]
    if missing_placeholders:
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail=f"args 模板缺少占位符：{', '.join(missing_placeholders)}。",
            path=executable,
        )

    return _make_check(
        key=f"tool_{tool_key}",
        label=label,
        status=PreflightCheckStatus.READY,
        detail="工具路径和参数模板都已配置。",
        path=executable,
    )


def _check_resource_package(
    manifest: ProjectManifest,
    game_root: Path,
    package_name: str,
    required: bool,
) -> PreflightCheck:
    relative_path = manifest.resource_package_map.get(package_name)
    if relative_path is None:
        return _make_check(
            key=f"package_{package_name}",
            label=package_name,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="项目清单中没有登记这个资源包。",
        )

    package_path = game_root / relative_path
    return _make_check(
        key=f"package_{package_name}",
        label=package_name,
        status=_status_for_requirement(package_path.exists(), required=required),
        detail="资源包已找到。" if package_path.exists() else "资源包在磁盘上不存在。",
        path=package_path,
    )


def _count_script_assets(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file() and _is_decompilable_script_asset(path))


def _count_json_files(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*.json") if path.is_file())


def _is_decompilable_script_asset(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".scn") or name.endswith(".psb") or name.endswith(".psb.m")


def _summarize_checks(checks: list[PreflightCheck]) -> PreflightCheckStatus:
    if any(check.status == PreflightCheckStatus.BLOCKED for check in checks):
        return PreflightCheckStatus.BLOCKED
    if any(check.status == PreflightCheckStatus.WARNING for check in checks):
        return PreflightCheckStatus.WARNING
    return PreflightCheckStatus.READY


def _recommend_commands(
    project_root: Path,
    config_path: str | None,
    check_map: dict[str, PreflightCheck],
    target_stage: PreflightStage,
) -> list[str]:
    command_prefix = "python -m duolingal"
    config_segment = f' --config "{config_path}"' if config_path else ""
    project_segment = f' "{project_root}"'

    if target_stage == PreflightStage.EXTRACT:
        if any(
            check_map[key].status == PreflightCheckStatus.BLOCKED
            for key in ("game_root", "package_voice.xp3", "package_scn.xp3", "tool_krkrextract")
        ):
            return [f'{command_prefix} list-tools{config_segment}'.strip()]
        return [f'{command_prefix} extract{project_segment}{config_segment}'.strip()]

    if target_stage == PreflightStage.DECOMPILE_SCRIPTS:
        if check_map["tool_freemote"].status == PreflightCheckStatus.BLOCKED:
            return [f'{command_prefix} list-tools{config_segment}'.strip()]
        if check_map["extracted_script_assets"].status == PreflightCheckStatus.BLOCKED:
            return [f'{command_prefix} extract{project_segment}{config_segment}'.strip()]
        return [f'{command_prefix} decompile-scripts{project_segment}{config_segment}'.strip()]

    if check_map["json_sources_for_build_lines"].status == PreflightCheckStatus.READY:
        return [f'{command_prefix} build-lines{project_segment}'.strip()]
    if check_map["tool_freemote"].status == PreflightCheckStatus.BLOCKED:
        return [f'{command_prefix} list-tools{config_segment}'.strip()]
    if check_map["extracted_script_assets"].status == PreflightCheckStatus.BLOCKED:
        return [f'{command_prefix} extract{project_segment}{config_segment}'.strip()]
    return [f'{command_prefix} decompile-scripts{project_segment}{config_segment}'.strip()]


def _status_for_requirement(ok: bool, required: bool) -> PreflightCheckStatus:
    if ok:
        return PreflightCheckStatus.READY
    return PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING


def _make_check(
    key: str,
    label: str,
    status: PreflightCheckStatus,
    detail: str,
    path: Path | None = None,
) -> PreflightCheck:
    return PreflightCheck(
        key=key,
        label=label,
        status=status,
        detail=detail,
        path=str(path) if path is not None else None,
    )
