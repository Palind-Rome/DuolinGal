from __future__ import annotations

import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.krkrdump import prepare_project_krkrdump
from duolingal.core.tool_config import load_toolchain_config
from duolingal.core.workspace import initialize_project_workspace


class KrkrDumpTests(unittest.TestCase):
    def test_prepare_project_krkrdump_writes_config_and_command(self) -> None:
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
            manifest = initialize_project_workspace(analysis, project_id="senren-krkrdump", projects_root=projects_root)

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
            config = load_toolchain_config(config_path)

            result = prepare_project_krkrdump(manifest.workspace_path, config)

            payload = json.loads((krkrdump_dir / "KrkrDump.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["outputDirectory"], str(projects_root / "senren-krkrdump" / "extracted_script"))
            self.assertIn(".scn", payload["includeExtensions"])
            self.assertTrue(payload["decryptSimpleCrypt"])
            self.assertIn("KrkrDumpLoader.exe", result.launch_command)
            self.assertTrue(result.game_executable.endswith("senrenbanka.exe"))


if __name__ == "__main__":
    unittest.main()
