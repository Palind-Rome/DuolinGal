from __future__ import annotations

from pathlib import Path
import json
import os

from duolingal.config import REPO_ROOT
from duolingal.domain.models import ToolConfigEntry, ToolchainConfig


DEFAULT_TOOLCHAIN_CONFIG_PATH = REPO_ROOT / "configs" / "toolchain.local.json"
TOOLCHAIN_ENV_VAR = "DUOLINGAL_TOOLCHAIN_CONFIG"


def load_toolchain_config(config_path: str | Path | None = None) -> ToolchainConfig:
    resolved_path = _resolve_config_path(config_path)
    if resolved_path is None or not resolved_path.exists():
        return ToolchainConfig(source_path=str(resolved_path) if resolved_path else None)

    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    tools = {
        key: ToolConfigEntry.model_validate(value)
        for key, value in payload.items()
        if isinstance(value, dict)
    }
    return ToolchainConfig(
        source_path=str(resolved_path),
        tools=tools,
    )


def _resolve_config_path(config_path: str | Path | None) -> Path | None:
    if config_path is not None:
        return Path(config_path).expanduser().resolve()

    env_path = os.getenv(TOOLCHAIN_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return DEFAULT_TOOLCHAIN_CONFIG_PATH
