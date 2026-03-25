from __future__ import annotations

from pathlib import Path
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


class AnalyzerTests(unittest.TestCase):
    def test_detects_senren_banka_layout(self) -> None:
        with temporary_workspace() as root:
            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(root / name)

            analysis = analyze_game_directory(root)

            self.assertTrue(analysis.exists)
            self.assertTrue(analysis.supported)
            self.assertEqual(analysis.game_id, "senren_banka")
            self.assertEqual(analysis.engine, "kirikiri_z")
            self.assertEqual(analysis.script_format, "scn_psb")

    def test_warns_when_core_packages_are_missing(self) -> None:
        with temporary_workspace() as root:
            touch(root / "game.exe")

            analysis = analyze_game_directory(root)

            self.assertFalse(analysis.supported)
            self.assertIn("未找到 voice.xp3，语音提取链路暂时无法确认。", analysis.warnings)
            self.assertIn("未找到 scn.xp3，脚本/场景提取链路暂时无法确认。", analysis.warnings)


if __name__ == "__main__":
    unittest.main()
