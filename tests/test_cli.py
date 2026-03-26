from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.cli import main
from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.workspace import initialize_project_workspace


class CliTests(unittest.TestCase):
    def test_extract_command_uses_configured_toolchain(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-cli", projects_root=projects_root)
            project_root = projects_root / "senren-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)
            config_path = temp_dir / "toolchain.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "krkrextract": {
                            "path": sys.executable,
                            "args": [
                                "-c",
                                (
                                    "import sys; from pathlib import Path; "
                                    "source = Path(sys.argv[1]); "
                                    "output = Path(sys.argv[2]); "
                                    "output.mkdir(parents=True, exist_ok=True); "
                                    "(output / 'done.txt').write_text(source.name, encoding='utf-8')"
                                ),
                                "{package}",
                                "{output}",
                            ],
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "extract",
                        str(project_root),
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(len(payload), 2)
            self.assertTrue((project_root / "extracted_voice" / "done.txt").exists())
            self.assertTrue((project_root / "extracted_script" / "done.txt").exists())

    def test_build_lines_command_outputs_summary_json(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-lines", projects_root=projects_root)
            project_root = projects_root / "senren-lines"
            self.assertEqual(str(project_root), manifest.workspace_path)
            script_dir = project_root / "extracted_script"
            script_dir.mkdir(parents=True, exist_ok=True)
            (script_dir / "scene001.json").write_text(
                json.dumps(
                    [
                        {
                            "speaker": "芳乃",
                            "voice": "yoshi_001.ogg",
                            "texts": {
                                "jp": "おはようございます。",
                                "en": "Good morning.",
                            },
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "build-lines",
                        str(project_root),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["node_count"], 1)
            self.assertEqual(payload["line_count"], 1)
            self.assertTrue((project_root / "dataset" / "lines.csv").exists())


if __name__ == "__main__":
    unittest.main()
