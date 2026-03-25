from __future__ import annotations

import argparse

from duolingal.services.project_service import ProjectService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="duolingal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="分析游戏目录。")
    analyze_parser.add_argument("game_path", help="游戏安装目录。")

    init_parser = subparsers.add_parser("init-project", help="初始化工作区。")
    init_parser.add_argument("game_path", help="游戏安装目录。")
    init_parser.add_argument("--project-id", help="自定义项目 ID。")

    subparsers.add_parser("list-tools", help="列出当前需要的外部工具及检测结果。")

    args = parser.parse_args(argv)
    service = ProjectService()

    if args.command == "analyze":
        analysis = service.analyze(args.game_path)
        print(analysis.model_dump_json(indent=2, exclude_none=True))
        return 0

    if args.command == "init-project":
        manifest = service.init_project(args.game_path, project_id=args.project_id)
        print(manifest.model_dump_json(indent=2, exclude_none=True))
        return 0

    if args.command == "list-tools":
        tools = service.list_tools()
        print("[")
        for index, tool in enumerate(tools):
            suffix = "," if index < len(tools) - 1 else ""
            print(tool.model_dump_json(indent=2, exclude_none=True) + suffix)
        print("]")
        return 0

    return 1
