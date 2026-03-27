from __future__ import annotations

import sys
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.decompiler import decompile_project_scripts
from duolingal.core.tool_config import ToolchainConfig
from duolingal.core.workspace import initialize_project_workspace
from duolingal.domain.models import ToolConfigEntry


class DecompilerTests(unittest.TestCase):
    def test_decompiles_known_script_assets_into_json_outputs(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-decompile", projects_root=projects_root)

            extracted_script_dir = projects_root / "senren-decompile" / "extracted_script"
            touch(extracted_script_dir / "scene001.scn")
            touch(extracted_script_dir / "routeA" / "scene002.psb")

            config = ToolchainConfig(
                tools={
                    "freemote": ToolConfigEntry(
                        path=sys.executable,
                        args=[
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
                    )
                }
            )

            results = decompile_project_scripts(manifest.workspace_path, config)

            self.assertEqual(len(results), 2)
            self.assertTrue((projects_root / "senren-decompile" / "decompiled_script" / "scene001.json").exists())
            self.assertTrue((projects_root / "senren-decompile" / "decompiled_script" / "routeA" / "scene002.json").exists())
            self.assertTrue((projects_root / "senren-decompile" / "logs" / "decompile-scene001.scn.json").exists())
            self.assertTrue(all(result.status.value == "succeeded" for result in results))


if __name__ == "__main__":
    unittest.main()
