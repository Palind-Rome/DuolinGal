from __future__ import annotations

from pathlib import Path
import json

from duolingal.core.process_runner import run_command
from duolingal.core.tool_config import ToolchainConfig
from duolingal.core.workspace import load_project_manifest
from duolingal.domain.models import CommandSpec, ExtractionPlan, ExtractionResult, ExtractionStatus, ProjectManifest


EXTRACTOR_TOOL_KEY = "krkrextract"
PACKAGE_OUTPUT_DIRS = {
    "voice.xp3": "extracted_voice",
    "scn.xp3": "extracted_script",
}


def extract_project_packages(
    project_root: str | Path,
    config: ToolchainConfig,
    package_names: list[str] | None = None,
    runner=run_command,
) -> list[ExtractionResult]:
    manifest = load_project_manifest(project_root)
    return extract_packages_from_manifest(manifest, config, package_names=package_names, runner=runner)


def extract_packages_from_manifest(
    manifest: ProjectManifest,
    config: ToolchainConfig,
    package_names: list[str] | None = None,
    runner=run_command,
) -> list[ExtractionResult]:
    tool_entry = config.tools.get(EXTRACTOR_TOOL_KEY)
    if tool_entry is None:
        raise ValueError("未配置 krkrextract。请在 toolchain.local.json 中提供路径和参数模板。")
    if not tool_entry.args:
        raise ValueError("krkrextract 缺少 args 模板。请至少提供 {package} 和 {output} 相关参数。")

    executable = Path(tool_entry.path).expanduser().resolve()
    if not executable.exists():
        raise ValueError(f"krkrextract 路径不存在：{executable}")

    project_path = Path(manifest.workspace_path)
    logs_dir = project_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    results: list[ExtractionResult] = []
    for package_name in _select_packages(manifest, package_names):
        relative_path = manifest.resource_package_map.get(package_name, package_name)
        source_package = Path(manifest.root_path) / relative_path
        if not source_package.exists():
            raise ValueError(f"资源包不存在：{source_package}")

        output_dir = project_path / _resolve_output_dir(relative_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        rendered_args = [
            _render_argument(
                token,
                package=source_package,
                output=output_dir,
                workspace=project_path,
            )
            for token in tool_entry.args
        ]
        plan = ExtractionPlan(
            package_name=package_name,
            package_path=str(source_package),
            output_dir=str(output_dir),
            tool_key=EXTRACTOR_TOOL_KEY,
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
        status = ExtractionStatus.SUCCEEDED if run.returncode == 0 else ExtractionStatus.FAILED
        log_path = logs_dir / f"extract-{Path(package_name).stem}.json"
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
            ExtractionResult(
                package_name=package_name,
                package_path=str(source_package),
                output_dir=str(output_dir),
                status=status,
                log_path=str(log_path),
                run=run,
            )
        )

    return results


def _select_packages(manifest: ProjectManifest, package_names: list[str] | None) -> list[str]:
    available = manifest.resource_packages
    if package_names is None:
        return [name for name in available if name in PACKAGE_OUTPUT_DIRS]

    requested = []
    for name in package_names:
        if name not in available:
            raise ValueError(f"项目中不存在资源包：{name}")
        requested.append(name)
    return requested


def _resolve_output_dir(relative_path: str) -> str:
    package_name = Path(relative_path).name.lower()
    if package_name in PACKAGE_OUTPUT_DIRS:
        return PACKAGE_OUTPUT_DIRS[package_name]
    return str(Path("raw_assets") / Path(relative_path).stem)


def _render_argument(token: str, package: Path, output: Path, workspace: Path) -> str:
    rendered = token
    replacements = {
        "{package}": str(package),
        "{output}": str(output),
        "{workspace}": str(workspace),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered
