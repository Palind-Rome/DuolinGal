from __future__ import annotations

import csv
import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.parser import build_lines_for_project, parse_script_json_file
from duolingal.core.workspace import initialize_project_workspace


class ParserTests(unittest.TestCase):
    def test_parses_nested_dialogue_candidates_from_json(self) -> None:
        with temporary_workspace() as temp_dir:
            script_root = temp_dir / "script"
            script_root.mkdir(parents=True, exist_ok=True)
            script_file = script_root / "scene001.json"
            script_file.write_text(
                json.dumps(
                    {
                        "scene": [
                            {
                                "speaker": "ムラサメ",
                                "voice": "mura_001.ogg",
                                "texts": {
                                    "jp": "おはようございます",
                                    "en": "Good morning.",
                                },
                            },
                            {
                                "name": "芳乃",
                                "storage": "yoshi_002.ogg",
                                "jp_text": "こんにちは",
                                "en_text": "Hello.",
                            },
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            nodes = parse_script_json_file(script_file, root=script_root)

            self.assertEqual(len(nodes), 2)
            self.assertEqual(nodes[0].speaker_name, "ムラサメ")
            self.assertEqual(nodes[0].en_text, "Good morning.")
            self.assertEqual(nodes[1].voice_file, "yoshi_002.ogg")

    def test_builds_lines_csv_for_project(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-demo", projects_root=projects_root)

            script_dir = projects_root / "senren-demo" / "extracted_script"
            (script_dir / "scene001.json").write_text(
                json.dumps(
                    [
                        {
                            "speaker": "ムラサメ",
                            "voice": "mura_001.ogg",
                            "texts": {
                                "jp": "おはようございます",
                                "en": "Good morning.",
                            },
                        },
                        {
                            "speaker": "芳乃",
                            "voice": "yoshi_002.ogg",
                            "texts": {
                                "jp": "こんにちは",
                                "en": "Hello.",
                            },
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = build_lines_for_project(manifest.workspace_path)

            self.assertEqual(result.node_count, 2)
            self.assertEqual(result.line_count, 2)
            self.assertTrue((projects_root / "senren-demo" / "dataset" / "lines.csv").exists())
            self.assertTrue((projects_root / "senren-demo" / "dataset" / "script_nodes.jsonl").exists())

            with (projects_root / "senren-demo" / "dataset" / "lines.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["status"], "ready")
            self.assertEqual(rows[1]["speaker_name"], "芳乃")


if __name__ == "__main__":
    unittest.main()
