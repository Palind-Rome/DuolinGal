from __future__ import annotations

import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()
from duolingal.core.analyzer import analyze_game_directory


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

    def test_detects_by_executable_keyword_and_case_insensitive_files(self) -> None:
        with temporary_workspace() as root:
            for name in ("VOICE.XP3", "SCN.XP3", "SenrenBanka.EXE"):
                touch(root / name)

            analysis = analyze_game_directory(root)

            self.assertTrue(analysis.supported)
            self.assertEqual(analysis.game_id, "senren_banka")
            self.assertEqual(analysis.confidence.value, "high")

    def test_warns_when_core_packages_are_missing(self) -> None:
        with temporary_workspace() as root:
            touch(root / "game.exe")

            analysis = analyze_game_directory(root)

            self.assertFalse(analysis.supported)
            self.assertIn("未找到 voice.xp3，语音提取链路暂时无法确认。", analysis.warnings)
            self.assertIn("未找到 scn.xp3，脚本/场景提取链路暂时无法确认。", analysis.warnings)


if __name__ == "__main__":
    unittest.main()
