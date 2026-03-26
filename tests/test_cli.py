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
    def test_prepare_krkrdump_command_writes_runtime_config(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            krkrdump_dir = temp_dir / "krkrdump"
            loader_path = krkrdump_dir / "KrkrDumpLoader.exe"
            dll_path = krkrdump_dir / "KrkrDump.dll"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)
            touch(loader_path)
            touch(dll_path)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-krkrdump-cli", projects_root=projects_root)
            project_root = projects_root / "senren-krkrdump-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)

            config_path = temp_dir / "toolchain.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "krkrdump": {
                            "path": str(loader_path),
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
                        "prepare-krkrdump",
                        str(project_root),
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["output_directory"], str(project_root / "extracted_script"))
            self.assertTrue((krkrdump_dir / "KrkrDump.json").exists())

    def test_preflight_command_outputs_next_recommended_step(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            fake_extract = temp_dir / "KrkrExtract.exe"
            fake_freemote = temp_dir / "PsbDecompile.exe"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)
            touch(fake_extract)
            touch(fake_freemote)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-preflight-cli", projects_root=projects_root)
            project_root = projects_root / "senren-preflight-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)

            config_path = temp_dir / "toolchain.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "krkrextract": {
                            "path": str(fake_extract),
                            "args": ["{package}", "{output}"],
                        },
                        "freemote": {
                            "path": str(fake_freemote),
                            "args": ["{input}", "{output}"],
                        },
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
                        "preflight",
                        str(project_root),
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["target_stage"], "build_lines")
            self.assertIn("extract", payload["recommended_commands"][0])

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

    def test_decompile_scripts_command_writes_json_outputs(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-decompile-cli", projects_root=projects_root)
            project_root = projects_root / "senren-decompile-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)

            extracted_script_dir = project_root / "extracted_script"
            touch(extracted_script_dir / "scene001.scn")

            config_path = temp_dir / "toolchain.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "freemote": {
                            "path": sys.executable,
                            "args": [
                                "-c",
                                (
                                    "import json, sys; from pathlib import Path; "
                                    "source = Path(sys.argv[1]); "
                                    "output = Path(sys.argv[2]); "
                                    "output.parent.mkdir(parents=True, exist_ok=True); "
                                    "payload = [{'speaker': 'Yoshino', 'voice': source.name + '.ogg', "
                                    "'texts': {'jp': 'jp-line', 'en': 'Good morning.'}}]; "
                                    "output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')"
                                ),
                                "{input}",
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
                        "decompile-scripts",
                        str(project_root),
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(len(payload), 1)
            self.assertTrue((project_root / "decompiled_script" / "scene001.scn.json").exists())

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
