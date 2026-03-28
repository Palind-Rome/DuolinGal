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
                                    "output_dir = Path(sys.argv[2]); "
                                    "output_dir.mkdir(parents=True, exist_ok=True); "
                                    "payload = [{'speaker': 'Yoshino', 'voice': source.name + '.ogg', "
                                    "'texts': {'jp': 'jp-line', 'en': 'Good morning.'}}]; "
                                    "(output_dir / (source.with_suffix('').name + '.json')).write_text("
                                    "json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')"
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
            self.assertTrue((project_root / "decompiled_script" / "scene001.json").exists())

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

    def test_prepare_poc_command_creates_game_ready_workspace(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            voice_root = temp_dir / "voice"
            voice_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-poc-cli", projects_root=projects_root)
            project_root = projects_root / "senren-poc-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)

            dataset_dir = project_root / "dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            with (dataset_dir / "lines.csv").open("w", encoding="utf-8", newline="") as handle:
                handle.write(
                    "line_id,scene_id,order_index,speaker_name,voice_file,jp_text,en_text,status,evidence\n"
                    "scene001-0001,scene001,1,Yoshino,yos100_001.ogg,jp-line,Good morning.,ready,voice_file|en_text|speaker_name|jp_text\n"
                )

            (voice_root / "yos100_001.ogg").write_bytes(b"dummy-ogg")

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-poc",
                        str(project_root),
                        str(voice_root),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["voice_file"], "yos100_001.ogg")
            self.assertTrue((project_root / "poc" / "scene001-0001" / "game-ready" / "unencrypted" / "yos100_001.ogg").exists())

    def test_prepare_patch_command_creates_patch_staging(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            source_root = temp_dir / "override"
            source_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-patch-cli", projects_root=projects_root)
            project_root = projects_root / "senren-patch-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)

            (source_root / "uts001_001.ogg").write_bytes(b"patch-data")

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-patch",
                        str(project_root),
                        str(source_root),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["archive_name"], "patch2")
            self.assertTrue((project_root / "patch-build" / "patch2" / "uts001_001.ogg").exists())

    def test_export_dataset_command_creates_speaker_dataset(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            voice_root = temp_dir / "voice"
            voice_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-dataset-cli", projects_root=projects_root)
            project_root = projects_root / "senren-dataset-cli"
            self.assertEqual(str(project_root), manifest.workspace_path)

            dataset_dir = project_root / "dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            with (dataset_dir / "lines.csv").open("w", encoding="utf-8", newline="") as handle:
                handle.write(
                    "line_id,scene_id,order_index,speaker_name,voice_file,jp_text,en_text,status,evidence\n"
                    "scene001-0001,scene001,1,Yoshino,yos100_001.ogg,jp-line,Good morning.,ready,voice_file|en_text|speaker_name|jp_text\n"
                )

            (voice_root / "yos100_001.ogg").write_bytes(b"dummy-ogg")

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "export-dataset",
                        str(project_root),
                        str(voice_root),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_count"], 1)
            self.assertTrue((project_root / "tts-dataset" / "yoshino" / "audio" / "yos100_001.ogg").exists())


if __name__ == "__main__":
    unittest.main()
