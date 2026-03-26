from __future__ import annotations

import sys
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.extractor import extract_project_packages
from duolingal.core.tool_config import ToolchainConfig
from duolingal.core.workspace import initialize_project_workspace
from duolingal.domain.models import ToolConfigEntry


class ExtractorTests(unittest.TestCase):
    def test_extracts_known_packages_into_workspace_directories(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-demo", projects_root=projects_root)

            config = ToolchainConfig(
                tools={
                    "krkrextract": ToolConfigEntry(
                        path=sys.executable,
                        args=[
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
                    )
                }
            )

            results = extract_project_packages(manifest.workspace_path, config)

            self.assertEqual(len(results), 2)
            self.assertTrue((projects_root / "senren-demo" / "extracted_voice" / "done.txt").exists())
            self.assertTrue((projects_root / "senren-demo" / "extracted_script" / "done.txt").exists())
            self.assertTrue((projects_root / "senren-demo" / "logs" / "extract-voice.json").exists())
            self.assertTrue(all(result.status.value == "succeeded" for result in results))


if __name__ == "__main__":
    unittest.main()
