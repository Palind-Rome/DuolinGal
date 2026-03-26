from __future__ import annotations

import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.preflight import run_project_preflight
from duolingal.core.workspace import initialize_project_workspace
from duolingal.domain.models import PreflightStage


class PreflightTests(unittest.TestCase):
    def test_prefers_prepare_krkrdump_when_runtime_dump_is_available(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            krkrdump_dir = temp_dir / "krkrdump"
            fake_loader = krkrdump_dir / "KrkrDumpLoader.exe"
            fake_dll = krkrdump_dir / "KrkrDump.dll"
            fake_freemote = temp_dir / "PsbDecompile.exe"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)
            touch(fake_loader)
            touch(fake_dll)
            touch(fake_freemote)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-preflight-krkrdump", projects_root=projects_root)

            config_path = temp_dir / "toolchain.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "krkrdump": {
                            "path": str(fake_loader),
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

            report = run_project_preflight(
                manifest.workspace_path,
                config_path=config_path,
                target_stage=PreflightStage.BUILD_LINES,
            )

            self.assertEqual(report.overall_status.value, "blocked")
            self.assertIn("prepare-krkrdump", report.recommended_commands[0])

    def test_recommends_extract_when_script_assets_are_missing(self) -> None:
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
            manifest = initialize_project_workspace(analysis, project_id="senren-preflight-extract", projects_root=projects_root)

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

            report = run_project_preflight(
                manifest.workspace_path,
                config_path=config_path,
                target_stage=PreflightStage.BUILD_LINES,
            )

            self.assertEqual(report.overall_status.value, "blocked")
            self.assertIn("extract", report.recommended_commands[0])

    def test_recommends_decompile_when_script_assets_exist_but_json_is_missing(self) -> None:
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
            manifest = initialize_project_workspace(analysis, project_id="senren-preflight-decompile", projects_root=projects_root)
            touch((projects_root / "senren-preflight-decompile" / "extracted_script" / "scene001.scn"))

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

            report = run_project_preflight(
                manifest.workspace_path,
                config_path=config_path,
                target_stage=PreflightStage.BUILD_LINES,
            )

            self.assertEqual(report.overall_status.value, "blocked")
            self.assertIn("decompile-scripts", report.recommended_commands[0])

    def test_build_lines_stage_is_ready_when_json_inputs_are_available(self) -> None:
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
            manifest = initialize_project_workspace(analysis, project_id="senren-preflight-ready", projects_root=projects_root)
            touch((projects_root / "senren-preflight-ready" / "extracted_script" / "scene001.scn"))
            (projects_root / "senren-preflight-ready" / "decompiled_script" / "scene001.scn.json").write_text(
                json.dumps(
                    [{"speaker": "Yoshino", "voice": "scene001.ogg", "texts": {"jp": "jp-line", "en": "Good morning."}}],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

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

            report = run_project_preflight(
                manifest.workspace_path,
                config_path=config_path,
                target_stage=PreflightStage.BUILD_LINES,
            )

            self.assertEqual(report.overall_status.value, "ready")
            self.assertIn("build-lines", report.recommended_commands[0])


if __name__ == "__main__":
    unittest.main()
