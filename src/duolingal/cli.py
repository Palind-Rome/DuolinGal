from __future__ import annotations

import argparse
import json

from duolingal.services.project_service import ProjectService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="duolingal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="分析游戏目录。")
    analyze_parser.add_argument("game_path", help="游戏安装目录。")

    init_parser = subparsers.add_parser("init-project", help="初始化工作区。")
    init_parser.add_argument("game_path", help="游戏安装目录。")
    init_parser.add_argument("--project-id", help="自定义项目 ID。")

    tools_parser = subparsers.add_parser("list-tools", help="列出当前需要的外部工具及检测结果。")
    tools_parser.add_argument("--config", help="可选的工具链配置文件路径。")

    extract_parser = subparsers.add_parser("extract", help="提取项目中的资源包。")
    extract_parser.add_argument("project_root", help="已初始化的项目工作区目录。")
    extract_parser.add_argument("--config", help="工具链配置文件路径。")
    extract_parser.add_argument("--package", dest="packages", action="append", help="只提取指定资源包，可重复传入。")

    decompile_parser = subparsers.add_parser("decompile-scripts", help="将提取出的 SCN/PSB 脚本反编译为 JSON。")
    decompile_parser.add_argument("project_root", help="已初始化的项目工作区目录。")
    decompile_parser.add_argument("--config", help="工具链配置文件路径。")
    decompile_parser.add_argument("--input-root", help="可选的原始脚本输入目录。")
    decompile_parser.add_argument("--output-root", help="可选的反编译输出目录。")

    lines_parser = subparsers.add_parser("build-lines", help="从脚本 JSON 构建 lines.csv。")
    lines_parser.add_argument("project_root", help="已初始化的项目工作区目录。")
    lines_parser.add_argument("--script-root", help="可选的脚本 JSON 根目录。")

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

    if args.command == "build-lines":
        result = service.build_lines(args.project_root, script_root=args.script_root)
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    return 1


def _emit_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
