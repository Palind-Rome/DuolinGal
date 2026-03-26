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
    needs_script_assets = target_stage in {PreflightStage.DECOMPILE_SCRIPTS, PreflightStage.BUILD_LINES} and not json_ready_for_build_lines

    krkrdump_ready = _krkrdump_ready(config, manifest)
    krkrextract_ready = _template_tool_ready(config, "krkrextract", ("{package}", "{output}"))
    freemote_ready = _template_tool_ready(config, "freemote", ("{input}", "{output}"))

    checks: list[PreflightCheck] = [
        _make_check(
            key="game_root",
            label="Game Root",
            status=_status_for_requirement(game_root.exists(), required=target_stage == PreflightStage.EXTRACT),
            detail="Game install directory is available." if game_root.exists() else "Game install directory is missing.",
            path=game_root,
        ),
        _make_check(
            key="primary_executable",
            label="Game Executable",
            status=_status_for_requirement(_resolve_executable_path(manifest).exists(), required=needs_script_assets),
            detail=(
                "A game executable is available for runtime dumping."
                if _resolve_executable_path(manifest).exists()
                else "No game executable could be resolved from the project manifest."
            ),
            path=_resolve_executable_path(manifest),
        ),
        _check_resource_package(
            manifest,
            game_root,
            "voice.xp3",
            required=False,
        ),
        _check_resource_package(
            manifest,
            game_root,
            "scn.xp3",
            required=False,
        ),
        _check_krkrdump_tool(config, manifest, required=needs_script_assets and extracted_script_assets == 0),
        _check_template_tool(
            config,
            tool_key="krkrextract",
            label="KrkrExtract",
            required_placeholders=("{package}", "{output}"),
            required=False,
            missing_detail="KrkrExtract is not configured as an offline fallback.",
        ),
        _make_check(
            key="script_extraction_backend",
            label="Script Extraction Backend",
            status=_status_for_requirement(
                extracted_script_assets > 0 or krkrdump_ready or krkrextract_ready,
                required=needs_script_assets,
            ),
            detail=_script_backend_detail(extracted_script_assets, krkrdump_ready, krkrextract_ready),
        ),
        _make_check(
            key="extracted_script_dir",
            label="Extracted Script Directory",
            status=_status_for_requirement(extracted_script_root.exists(), required=needs_script_assets),
            detail=(
                f"Extracted script directory exists with {extracted_script_assets} candidate assets."
                if extracted_script_root.exists()
                else "The extracted_script directory does not exist yet."
            ),
            path=extracted_script_root,
        ),
        _make_check(
            key="extracted_script_assets",
            label="Candidate Script Assets",
            status=_status_for_requirement(extracted_script_assets > 0, required=needs_script_assets),
            detail=(
                f"Found {extracted_script_assets} .scn/.psb/.psb.m files."
                if extracted_script_assets > 0
                else "No .scn/.psb/.psb.m files are available yet."
            ),
            path=extracted_script_root,
        ),
        _check_template_tool(
            config,
            tool_key="freemote",
            label="FreeMote",
            required_placeholders=("{input}", "{output}"),
            required=target_stage != PreflightStage.EXTRACT and extracted_script_assets > 0 and not json_ready_for_build_lines,
            missing_detail="FreeMote is required to decompile SCN/PSB assets into JSON.",
        ),
        _make_check(
            key="decompiled_script_json",
            label="Decompiled JSON",
            status=_status_for_requirement(decompiled_json_files > 0, required=False),
            detail=(
                f"Found {decompiled_json_files} decompiled JSON files."
                if decompiled_json_files > 0
                else "The decompiled_script directory does not contain JSON yet."
            ),
            path=decompiled_script_root,
        ),
        _make_check(
            key="json_sources_for_build_lines",
            label="JSON Sources For build-lines",
            status=_status_for_requirement(json_ready_for_build_lines, required=target_stage == PreflightStage.BUILD_LINES),
            detail=(
                f"Found {decompiled_json_files + extracted_json_files} JSON inputs for build-lines."
                if json_ready_for_build_lines
                else "No JSON sources are available for build-lines yet."
            ),
            path=decompiled_script_root if decompiled_json_files > 0 else extracted_script_root,
        ),
    ]

    return checks


def _check_krkrdump_tool(
    config: ToolchainConfig,
    manifest: ProjectManifest,
    required: bool,
) -> PreflightCheck:
    entry = config.tools.get("krkrdump")
    if entry is None:
        return _make_check(
            key="tool_krkrdump",
            label="KrkrDump",
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.READY,
            detail="KrkrDump is not configured, but it is not required for the current stage.",
        )

    loader_path = Path(entry.path).expanduser().resolve()
    if not loader_path.exists():
        return _make_check(
            key="tool_krkrdump",
            label="KrkrDump",
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="KrkrDumpLoader.exe path does not exist.",
            path=loader_path,
        )

    dll_path = loader_path.with_name("KrkrDump.dll")
    if not dll_path.exists():
        return _make_check(
            key="tool_krkrdump",
            label="KrkrDump",
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="KrkrDump.dll was not found next to the loader.",
            path=dll_path,
        )

    executable_path = _resolve_executable_path(manifest)
    if not executable_path.exists():
        return _make_check(
            key="tool_krkrdump",
            label="KrkrDump",
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail="The project does not currently resolve a runnable game executable.",
            path=executable_path,
        )

    return _make_check(
        key="tool_krkrdump",
        label="KrkrDump",
        status=PreflightCheckStatus.READY,
        detail="KrkrDump loader, DLL, and game executable are ready.",
        path=loader_path,
    )


def _check_template_tool(
    config: ToolchainConfig,
    tool_key: str,
    label: str,
    required_placeholders: tuple[str, ...],
    required: bool,
    missing_detail: str,
) -> PreflightCheck:
    entry = config.tools.get(tool_key)
    if entry is None:
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.READY,
            detail=missing_detail if required else f"{label} is not configured, but it is optional for the current stage.",
        )

    executable = Path(entry.path).expanduser().resolve()
    if not executable.exists():
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail=f"{label} path does not exist.",
            path=executable,
        )

    if not entry.args:
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail=f"{label} is missing an args template.",
            path=executable,
        )

    joined_args = " ".join(entry.args)
    missing_placeholders = [placeholder for placeholder in required_placeholders if placeholder not in joined_args]
    if missing_placeholders:
        return _make_check(
            key=f"tool_{tool_key}",
            label=label,
            status=PreflightCheckStatus.BLOCKED if required else PreflightCheckStatus.WARNING,
            detail=f"{label} args are missing placeholders: {', '.join(missing_placeholders)}.",
            path=executable,
        )

    return _make_check(
        key=f"tool_{tool_key}",
        label=label,
        status=PreflightCheckStatus.READY,
        detail=f"{label} path and args template are configured.",
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
            detail="The project manifest does not list this resource package.",
        )

    package_path = game_root / relative_path
    return _make_check(
        key=f"package_{package_name}",
        label=package_name,
        status=_status_for_requirement(package_path.exists(), required=required),
        detail="Resource package exists." if package_path.exists() else "Resource package is missing on disk.",
        path=package_path,
    )


def _resolve_executable_path(manifest: ProjectManifest) -> Path:
    game_root = Path(manifest.root_path).resolve()
    if manifest.primary_executable:
        return (game_root / manifest.primary_executable).resolve()

    candidates = sorted(game_root.glob("*.exe"), key=lambda path: path.name.lower())
    if candidates:
        return candidates[0].resolve()
    return (game_root / "missing-game.exe").resolve()


def _krkrdump_ready(config: ToolchainConfig, manifest: ProjectManifest) -> bool:
    entry = config.tools.get("krkrdump")
    if entry is None:
        return False
    loader_path = Path(entry.path).expanduser().resolve()
    dll_path = loader_path.with_name("KrkrDump.dll")
    return loader_path.exists() and dll_path.exists() and _resolve_executable_path(manifest).exists()


def _template_tool_ready(
    config: ToolchainConfig,
    tool_key: str,
    required_placeholders: tuple[str, ...],
) -> bool:
    entry = config.tools.get(tool_key)
    if entry is None:
        return False

    executable = Path(entry.path).expanduser().resolve()
    if not executable.exists() or not entry.args:
        return False

    joined_args = " ".join(entry.args)
    return all(placeholder in joined_args for placeholder in required_placeholders)


def _script_backend_detail(
    extracted_script_assets: int,
    krkrdump_ready: bool,
    krkrextract_ready: bool,
) -> str:
    if extracted_script_assets > 0:
        return "Script assets are already present in extracted_script."
    backends: list[str] = []
    if krkrdump_ready:
        backends.append("KrkrDump")
    if krkrextract_ready:
        backends.append("KrkrExtract")
    if backends:
        return f"Available backend(s): {', '.join(backends)}."
    return "No script extraction backend is ready."


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
        if check_map["tool_krkrdump"].status == PreflightCheckStatus.READY:
            return [f'{command_prefix} prepare-krkrdump{project_segment}{config_segment}'.strip()]
        if check_map["tool_krkrextract"].status == PreflightCheckStatus.READY:
            return [f'{command_prefix} extract{project_segment}{config_segment}'.strip()]
        return [f'{command_prefix} list-tools{config_segment}'.strip()]

    if check_map["json_sources_for_build_lines"].status == PreflightCheckStatus.READY:
        return [f'{command_prefix} build-lines{project_segment}'.strip()]

    if check_map["extracted_script_assets"].status != PreflightCheckStatus.READY:
        if check_map["tool_krkrdump"].status == PreflightCheckStatus.READY:
            return [f'{command_prefix} prepare-krkrdump{project_segment}{config_segment}'.strip()]
        if check_map["tool_krkrextract"].status == PreflightCheckStatus.READY:
            return [f'{command_prefix} extract{project_segment}{config_segment}'.strip()]
        return [f'{command_prefix} list-tools{config_segment}'.strip()]

    if check_map["tool_freemote"].status == PreflightCheckStatus.READY:
        return [f'{command_prefix} decompile-scripts{project_segment}{config_segment}'.strip()]

    return [f'{command_prefix} list-tools{config_segment}'.strip()]


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
