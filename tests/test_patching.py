from __future__ import annotations

import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.patching import prepare_patch_staging
from duolingal.core.workspace import initialize_project_workspace


class PatchPreparationTests(unittest.TestCase):
    def test_prepare_patch_staging_defaults_to_patch2_when_patch_exists(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            source_root = temp_dir / "override"
            source_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            (source_root / "uts001_001.ogg").write_bytes(b"dummy")

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-patch", projects_root=projects_root)

            result = prepare_patch_staging(manifest.workspace_path, source_root)

            self.assertEqual(result.archive_name, "patch2")
            self.assertTrue((projects_root / "senren-patch" / "patch-build" / "patch2" / "uts001_001.ogg").exists())
            manifest_payload = json.loads((projects_root / "senren-patch" / "patch-build" / "patch2.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest_payload["copied_files"], ["uts001_001.ogg"])
            script_text = (projects_root / "senren-patch" / "patch-build" / "pack-patch2.ps1").read_text(encoding="utf-8")
            self.assertIn("$PSScriptRoot", script_text)
            self.assertIn("Xp3Pack.exe", script_text)

    def test_prepare_patch_staging_preserves_subdirectories(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            source_root = temp_dir / "override"
            nested_dir = source_root / "voice"
            nested_dir.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            (nested_dir / "line001.ogg").write_bytes(b"nested")

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-patch-nested", projects_root=projects_root)

            result = prepare_patch_staging(manifest.workspace_path, source_root, archive_name="patch9")

            self.assertEqual(result.archive_name, "patch9")
            self.assertTrue((projects_root / "senren-patch-nested" / "patch-build" / "patch9" / "voice" / "line001.ogg").exists())


if __name__ == "__main__":
    unittest.main()
