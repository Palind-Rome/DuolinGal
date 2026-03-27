from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from duolingal.core.tool_config import ToolchainConfig
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import KrkrDumpPreparationResult, ProjectManifest


KRKRDUMP_TOOL_KEY = "krkrdump"
DEFAULT_LOG_LEVEL = 2
DEFAULT_INCLUDE_EXTENSIONS = [
    ".scn",
    ".psb",
    ".psb.m",
    ".ks",
    ".tjs",
    ".txt",
    ".csv",
]
DEFAULT_RULES = [
    r"file://\./.+?\.xp3>(.+?\..+$)",
    r"archive://./(.+)",
    r"arc://./(.+)",
    r"bres://./(.+)",
]


def prepare_project_krkrdump(
    project_root: str | Path,
    config: ToolchainConfig,
    output_root: str | Path | None = None,
) -> KrkrDumpPreparationResult:
    manifest = load_project_manifest(project_root)
    return prepare_krkrdump_from_manifest(manifest, config, output_root=output_root)


def prepare_krkrdump_from_manifest(
    manifest: ProjectManifest,
    config: ToolchainConfig,
    output_root: str | Path | None = None,
) -> KrkrDumpPreparationResult:
    tool_entry = config.tools.get(KRKRDUMP_TOOL_KEY)
    if tool_entry is None:
        raise ValueError(
            "KrkrDump is not configured. Add a `krkrdump` entry to toolchain.local.json "
            "and point it to KrkrDumpLoader.exe."
        )

    loader_path = Path(tool_entry.path).expanduser().resolve()
    if not loader_path.exists():
        raise ValueError(f"KrkrDump loader path does not exist: {loader_path}")

    dll_path = loader_path.with_name("KrkrDump.dll")
    if not dll_path.exists():
        raise ValueError(f"KrkrDump.dll was not found next to the loader: {dll_path}")

    project_path = Path(manifest.workspace_path).resolve()
    output_directory = (
        Path(output_root).expanduser().resolve()
        if output_root is not None
        else (project_path / "extracted_script").resolve()
    )
    output_directory.mkdir(parents=True, exist_ok=True)

    game_executable = _resolve_game_executable(manifest)
    config_path = loader_path.with_name("KrkrDump.json")
    backup_config_path = _backup_existing_config(config_path)

    config_payload = {
        "loglevel": DEFAULT_LOG_LEVEL,
        "enableExtract": True,
        "outputDirectory": str(output_directory),
        "includeExtensions": DEFAULT_INCLUDE_EXTENSIONS,
        "excludeExtensions": [],
        "decryptSimpleCrypt": True,
        "rules": DEFAULT_RULES,
    }
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    launch_command = f'& "{loader_path}" "{game_executable}"'
    notes = [
        "This command is inferred from the official drag-and-drop workflow in the KrkrDump README.",
        "The prepared config is script-focused and does not try to dump audio assets yet.",
        "KrkrDump.json stays next to KrkrDumpLoader.exe because that is how the upstream tool discovers it.",
    ]
    if backup_config_path is not None:
        notes.append("An existing KrkrDump.json was backed up before writing the new config.")

    return KrkrDumpPreparationResult(
        project_root=str(project_path),
        game_executable=str(game_executable),
        loader_path=str(loader_path),
        dll_path=str(dll_path),
        config_path=str(config_path),
        output_directory=str(output_directory),
        launch_command=launch_command,
        backup_config_path=backup_config_path,
        notes=notes,
    )


def _resolve_game_executable(manifest: ProjectManifest) -> Path:
    game_root = Path(manifest.root_path).resolve()

    candidates: list[Path] = []
    if manifest.primary_executable:
        primary_candidate = game_root / manifest.primary_executable
        if _looks_like_game_executable(primary_candidate):
            candidates.append(primary_candidate)

    candidates.extend(_preferred_game_executables(game_root))
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            return candidate.resolve()

    raise ValueError(f"No game executable was found under: {game_root}")


def _preferred_game_executables(game_root: Path) -> list[Path]:
    executables = sorted(game_root.glob("*.exe"), key=lambda path: path.name.lower())
    preferred = [path for path in executables if _looks_like_game_executable(path)]
    if preferred:
        return preferred
    return executables


def _looks_like_game_executable(path: Path) -> bool:
    helper_markers = ("dump", "loader", "extract", "patch", "unins", "setup", "config")
    stem = path.stem.lower()
    return not any(marker in stem for marker in helper_markers)


def _backup_existing_config(config_path: Path) -> str | None:
    if not config_path.exists():
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = config_path.with_name(f"{config_path.stem}.{timestamp}.bak{config_path.suffix}")
    backup_path.write_bytes(config_path.read_bytes())
    return str(backup_path)
