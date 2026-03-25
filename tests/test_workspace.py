from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.workspace import initialize_project_workspace


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


@contextmanager
def temporary_workspace() -> Path:
    root = ROOT / ".tmp-tests"
    root.mkdir(parents=True, exist_ok=True)
    temp_dir = root / f"case-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class WorkspaceTests(unittest.TestCase):
    def test_initializes_project_workspace_and_manifest(self) -> None:
        with temporary_workspace() as temp_dir:
            root = temp_dir / "game"
            projects = temp_dir / "projects"
            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(root / name)

            analysis = analyze_game_directory(root)
            manifest = initialize_project_workspace(analysis, project_id="senren-demo", projects_root=projects)

            manifest_path = projects / "senren-demo" / "project_manifest.json"
            snapshot_path = projects / "senren-demo" / "directory_snapshot.json"

            self.assertTrue(manifest_path.exists())
            self.assertTrue(snapshot_path.exists())
            self.assertEqual(manifest.project_id, "senren-demo")

            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["game_id"], "senren_banka")
            self.assertEqual(payload["engine"], "kirikiri_z")


if __name__ == "__main__":
    unittest.main()
