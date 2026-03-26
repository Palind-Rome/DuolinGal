from __future__ import annotations

import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.workspace import initialize_project_workspace


class WorkspaceTests(unittest.TestCase):
    def test_initializes_project_workspace_and_manifest(self) -> None:
        with temporary_workspace() as temp_dir:
            root = temp_dir / "game"
            projects = temp_dir / "projects"
            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(root / name)

            analysis = analyze_game_directory(root)
            manifest = initialize_project_workspace(analysis, project_id="senren-demo", projects_root=projects)

            project_root = projects / "senren-demo"
            manifest_path = project_root / "project_manifest.json"
            snapshot_path = project_root / "directory_snapshot.json"

            self.assertTrue(manifest_path.exists())
            self.assertTrue(snapshot_path.exists())
            self.assertTrue((project_root / "decompiled_script").exists())
            self.assertEqual(manifest.project_id, "senren-demo")

            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["game_id"], "senren_banka")
            self.assertEqual(payload["engine"], "kirikiri_z")
            self.assertEqual(payload["resource_package_map"]["voice.xp3"], "voice.xp3")


if __name__ == "__main__":
    unittest.main()
