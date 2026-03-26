from __future__ import annotations

from pathlib import Path
import json

from duolingal.core.process_runner import run_command
from duolingal.core.tool_config import ToolchainConfig
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import (
    CommandSpec,
    DecompileStatus,
    ProjectManifest,
    ScriptDecompilePlan,
    ScriptDecompileResult,
)


DECOMPILER_TOOL_KEY = "freemote"
DEFAULT_INPUT_DIR = "extracted_script"
DEFAULT_OUTPUT_DIR = "decompiled_script"


def decompile_project_scripts(
    project_root: str | Path,
    config: ToolchainConfig,
    input_root: str | Path | None = None,
    output_root: str | Path | None = None,
    runner=run_command,
) -> list[ScriptDecompileResult]:
    manifest = load_project_manifest(project_root)
    return decompile_scripts_from_manifest(
        manifest,
        config,
        input_root=input_root,
        output_root=output_root,
        runner=runner,
    )


def decompile_scripts_from_manifest(
    manifest: ProjectManifest,
    config: ToolchainConfig,
    input_root: str | Path | None = None,
    output_root: str | Path | None = None,
    runner=run_command,
) -> list[ScriptDecompileResult]:
    tool_entry = config.tools.get(DECOMPILER_TOOL_KEY)
    if tool_entry is None:
        raise ValueError("未配置 freemote。请在 toolchain.local.json 中提供路径和参数模板。")
    if not tool_entry.args:
        raise ValueError("freemote 缺少 args 模板。请至少提供 {input} 和 {output} 相关参数。")

    executable = Path(tool_entry.path).expanduser().resolve()
    if not executable.exists():
        raise ValueError(f"freemote 路径不存在：{executable}")

    project_path = Path(manifest.workspace_path)
    source_root = Path(input_root) if input_root is not None else project_path / DEFAULT_INPUT_DIR
    source_root = source_root.expanduser().resolve()
    if not source_root.exists():
        raise ValueError(f"未找到待反编译脚本目录：{source_root}")

    target_root = Path(output_root) if output_root is not None else project_path / DEFAULT_OUTPUT_DIR
    target_root = target_root.expanduser().resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    logs_dir = project_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    candidates = list(_iter_script_assets(source_root))
    if not candidates:
        raise ValueError(f"在 {source_root} 下未找到可反编译的 .scn/.psb/.psb.m 文件。")

    results: list[ScriptDecompileResult] = []
    for source_path in candidates:
        relative_path = source_path.relative_to(source_root)
        output_path = target_root / relative_path.parent / f"{relative_path.name}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rendered_args = [
            _render_argument(
                token,
                input_path=source_path,
                output_path=output_path,
                workspace=project_path,
            )
            for token in tool_entry.args
        ]
        plan = ScriptDecompilePlan(
            source_path=str(source_path),
            output_path=str(output_path),
            tool_key=DECOMPILER_TOOL_KEY,
            command=[str(executable), *rendered_args],
        )

        run = runner(
            CommandSpec(
                executable=str(executable),
                args=rendered_args,
                cwd=str(project_path),
                env=tool_entry.env,
            )
        )
        status = DecompileStatus.SUCCEEDED if run.returncode == 0 else DecompileStatus.FAILED
        log_name = relative_path.as_posix().replace("/", "__") + ".json"
        log_path = logs_dir / f"decompile-{log_name}"
        log_path.write_text(
            json.dumps(
                {
                    "plan": plan.model_dump(mode="json"),
                    "run": run.model_dump(mode="json"),
                    "status": status.value,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        results.append(
            ScriptDecompileResult(
                source_path=str(source_path),
                output_path=str(output_path),
                status=status,
                log_path=str(log_path),
                run=run,
            )
        )

    return results


def _iter_script_assets(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and _is_decompilable_script_asset(path)
    ]


def _is_decompilable_script_asset(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".scn") or name.endswith(".psb") or name.endswith(".psb.m")


def _render_argument(token: str, input_path: Path, output_path: Path, workspace: Path) -> str:
    rendered = token
    replacements = {
        "{input}": str(input_path),
        "{output}": str(output_path),
        "{workspace}": str(workspace),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered
