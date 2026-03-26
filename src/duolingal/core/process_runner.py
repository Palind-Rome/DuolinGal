from __future__ import annotations

from pathlib import Path
import os
import subprocess
import time

from duolingal.domain.models import CommandResult, CommandSpec


def run_command(spec: CommandSpec) -> CommandResult:
    start = time.perf_counter()
    completed = subprocess.run(
        [spec.executable, *spec.args],
        cwd=spec.cwd,
        env=_merge_environment(spec.env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=spec.timeout_seconds,
        check=False,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return CommandResult(
        command=[spec.executable, *spec.args],
        cwd=spec.cwd,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=duration_ms,
    )


def _merge_environment(overrides: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(overrides)
    return env
