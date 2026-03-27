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
    def test_parses_senren_scene_text_entries(self) -> None:
        with temporary_workspace() as temp_dir:
            script_root = temp_dir / "script"
            script_root.mkdir(parents=True, exist_ok=True)
            script_file = script_root / "scene001.ks.json"
            script_file.write_text(
                json.dumps(
                    {
                        "name": "scene001.ks",
                        "scenes": [
                            {
                                "label": "*start",
                                "title": "Opening",
                                "texts": [
                                    [
                                        "芳乃",
                                        None,
                                        [
                                            [None, "「……はぁ……」"],
                                            ["Yoshino", "Haah..."],
                                            ["芳乃", "「……呼……」"],
                                            ["芳乃", "「……呼……」"],
                                        ],
                                        [
                                            {
                                                "name": "芳乃",
                                                "voice": "yos100_001",
                                            }
                                        ],
                                        1216,
                                        {"data": []},
                                    ],
                                    [
                                        None,
                                        None,
                                        [
                                            [None, "地の文です。"],
                                            [None, "Narration line."],
                                            [None, "这是旁白。"],
                                            [None, "這是旁白。"],
                                        ],
                                        None,
                                        200,
                                        {"data": []},
                                    ],
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            nodes = parse_script_json_file(script_file, root=script_root)

            self.assertEqual(len(nodes), 2)
            self.assertEqual(nodes[0].speaker_name, "芳乃")
            self.assertEqual(nodes[0].voice_file, "yos100_001.ogg")
            self.assertEqual(nodes[0].jp_text, "「……はぁ……」")
            self.assertEqual(nodes[0].en_text, "Haah...")
            self.assertEqual(nodes[0].metadata["cn_text"], "「……呼……」")
            self.assertEqual(nodes[0].metadata["duration_ms"], "1216")
            self.assertEqual(nodes[1].speaker_name, None)
            self.assertEqual(nodes[1].en_text, "Narration line.")

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
                                "speaker": "Murasame",
                                "voice": "mura_001.ogg",
                                "texts": {
                                    "jp": "jp-line-1",
                                    "en": "Good morning.",
                                },
                            },
                            {
                                "name": "Yoshino",
                                "storage": "yoshi_002.ogg",
                                "jp_text": "jp-line-2",
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
            self.assertEqual(nodes[0].speaker_name, "Murasame")
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
                            "speaker": "Murasame",
                            "voice": "mura_001.ogg",
                            "texts": {
                                "jp": "jp-line-1",
                                "en": "Good morning.",
                            },
                        },
                        {
                            "speaker": "Yoshino",
                            "voice": "yoshi_002.ogg",
                            "texts": {
                                "jp": "jp-line-2",
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
            self.assertEqual(rows[1]["speaker_name"], "Yoshino")

    def test_prefers_decompiled_script_directory_when_json_exists(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-preferred", projects_root=projects_root)

            extracted_script_dir = projects_root / "senren-preferred" / "extracted_script"
            decompiled_script_dir = projects_root / "senren-preferred" / "decompiled_script"

            (extracted_script_dir / "ignored.json").write_text(
                json.dumps(
                    [
                        {
                            "speaker": "Ignored",
                            "voice": "ignored.ogg",
                            "texts": {
                                "jp": "ignored-jp",
                                "en": "This should not be used.",
                            },
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (decompiled_script_dir / "scene001.scn.json").write_text(
                json.dumps(
                    [
                        {
                            "speaker": "Yoshino",
                            "voice": "yoshi_001.ogg",
                            "texts": {
                                "jp": "jp-line",
                                "en": "Good morning.",
                            },
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = build_lines_for_project(manifest.workspace_path)

            self.assertEqual(result.script_root, str(decompiled_script_dir.resolve()))
            with (projects_root / "senren-preferred" / "dataset" / "lines.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["speaker_name"], "Yoshino")

    def test_ignores_resx_json_sidecars(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-sidecars", projects_root=projects_root)

            decompiled_script_dir = projects_root / "senren-sidecars" / "decompiled_script"
            (decompiled_script_dir / "scene001.json").write_text(
                json.dumps(
                    [
                        {
                            "speaker": "Yoshino",
                            "voice": "yoshi_001.ogg",
                            "texts": {
                                "jp": "jp-line",
                                "en": "Good morning.",
                            },
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (decompiled_script_dir / "scene001.resx.json").write_text(
                json.dumps({"resources": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = build_lines_for_project(manifest.workspace_path)

            self.assertEqual(result.scene_count, 1)
            self.assertEqual(result.node_count, 1)


if __name__ == "__main__":
    unittest.main()
