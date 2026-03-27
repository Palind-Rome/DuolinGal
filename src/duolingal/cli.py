from __future__ import annotations

import argparse
import json

from duolingal.domain.models import PreflightStage
from duolingal.services.project_service import ProjectService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="duolingal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a game installation directory.")
    analyze_parser.add_argument("game_path", help="Game installation directory.")

    init_parser = subparsers.add_parser("init-project", help="Initialize a project workspace.")
    init_parser.add_argument("game_path", help="Game installation directory.")
    init_parser.add_argument("--project-id", help="Optional project identifier override.")

    tools_parser = subparsers.add_parser("list-tools", help="List external tool requirements and detection results.")
    tools_parser.add_argument("--config", help="Optional toolchain config path.")

    extract_parser = subparsers.add_parser("extract", help="Extract configured resource packages with an offline tool.")
    extract_parser.add_argument("project_root", help="Initialized project workspace.")
    extract_parser.add_argument("--config", help="Toolchain config path.")
    extract_parser.add_argument("--package", dest="packages", action="append", help="Specific resource package to extract.")

    decompile_parser = subparsers.add_parser("decompile-scripts", help="Decompile SCN or PSB assets into JSON.")
    decompile_parser.add_argument("project_root", help="Initialized project workspace.")
    decompile_parser.add_argument("--config", help="Toolchain config path.")
    decompile_parser.add_argument("--input-root", help="Optional source asset root.")
    decompile_parser.add_argument("--output-root", help="Optional JSON output root.")

    krkrdump_parser = subparsers.add_parser(
        "prepare-krkrdump",
        help="Generate KrkrDump.json and print the local launch command.",
    )
    krkrdump_parser.add_argument("project_root", help="Initialized project workspace.")
    krkrdump_parser.add_argument("--config", help="Toolchain config path.")
    krkrdump_parser.add_argument("--output-root", help="Optional override for KrkrDump output directory.")

    preflight_parser = subparsers.add_parser("preflight", help="Check whether the project is ready for the next stage.")
    preflight_parser.add_argument("project_root", help="Initialized project workspace.")
    preflight_parser.add_argument("--config", help="Toolchain config path.")
    preflight_parser.add_argument(
        "--stage",
        choices=[stage.value for stage in PreflightStage],
        default=PreflightStage.BUILD_LINES.value,
        help="Target stage to validate.",
    )

    lines_parser = subparsers.add_parser("build-lines", help="Build lines.csv from script JSON.")
    lines_parser.add_argument("project_root", help="Initialized project workspace.")
    lines_parser.add_argument("--script-root", help="Optional script JSON root.")

    args = parser.parse_args(argv)
    service = ProjectService()

    if args.command == "analyze":
        analysis = service.analyze(args.game_path)
        _emit_json(analysis.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "init-project":
        manifest = service.init_project(args.game_path, project_id=args.project_id)
        _emit_json(manifest.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "list-tools":
        tools = service.list_tools(config_path=args.config)
        _emit_json([tool.model_dump(mode="json", exclude_none=True) for tool in tools])
        return 0

    if args.command == "extract":
        results = service.extract(
            args.project_root,
            config_path=args.config,
            package_names=args.packages,
        )
        _emit_json([result.model_dump(mode="json", exclude_none=True) for result in results])
        return 0

    if args.command == "decompile-scripts":
        results = service.decompile_scripts(
            args.project_root,
            config_path=args.config,
            input_root=args.input_root,
            output_root=args.output_root,
        )
        _emit_json([result.model_dump(mode="json", exclude_none=True) for result in results])
        return 0

    if args.command == "prepare-krkrdump":
        result = service.prepare_krkrdump(
            args.project_root,
            config_path=args.config,
            output_root=args.output_root,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "preflight":
        result = service.preflight(
            args.project_root,
            config_path=args.config,
            target_stage=PreflightStage(args.stage),
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "build-lines":
        result = service.build_lines(args.project_root, script_root=args.script_root)
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    return 1


def _emit_json(payload: object) -> None:
    pretty_json = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(pretty_json)
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
