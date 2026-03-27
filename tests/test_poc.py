from __future__ import annotations

import csv
import json
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.poc import prepare_single_line_poc
from duolingal.core.workspace import initialize_project_workspace


class PocTests(unittest.TestCase):
    def test_prepare_single_line_poc_creates_workspace_and_copies_voice(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            voice_root = temp_dir / "voice"
            voice_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-poc", projects_root=projects_root)

            dataset_dir = projects_root / "senren-poc" / "dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            with (dataset_dir / "lines.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "line_id",
                        "scene_id",
                        "order_index",
                        "speaker_name",
                        "voice_file",
                        "jp_text",
                        "en_text",
                        "status",
                        "evidence",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "line_id": "scene001-0001",
                        "scene_id": "scene001",
                        "order_index": "1",
                        "speaker_name": "Yoshino",
                        "voice_file": "yos100_001.ogg",
                        "jp_text": "「……はぁ……」",
                        "en_text": "Haah...",
                        "status": "ready",
                        "evidence": "voice_file|en_text|speaker_name|jp_text",
                    }
                )

            source_voice = voice_root / "yos100_001.ogg"
            source_voice.write_bytes(b"dummy-ogg")

            result = prepare_single_line_poc(manifest.workspace_path, voice_root)

            self.assertEqual(result.line_id, "scene001-0001")
            self.assertTrue((projects_root / "senren-poc" / "poc" / "scene001-0001" / "original" / "yos100_001.ogg").exists())
            self.assertTrue(
                (projects_root / "senren-poc" / "poc" / "scene001-0001" / "game-ready" / "unencrypted" / "yos100_001.ogg").exists()
            )
            metadata = json.loads((projects_root / "senren-poc" / "poc" / "scene001-0001" / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["voice_file"], "yos100_001.ogg")

    def test_prepare_single_line_poc_honors_filters(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            voice_root = temp_dir / "voice"
            voice_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-poc-filters", projects_root=projects_root)

            dataset_dir = projects_root / "senren-poc-filters" / "dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            with (dataset_dir / "lines.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "line_id",
                        "scene_id",
                        "order_index",
                        "speaker_name",
                        "voice_file",
                        "jp_text",
                        "en_text",
                        "status",
                        "evidence",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "line_id": "scene001-0001",
                        "scene_id": "scene001",
                        "order_index": "1",
                        "speaker_name": "Yoshino",
                        "voice_file": "yos100_001.ogg",
                        "jp_text": "jp-1",
                        "en_text": "Morning.",
                        "status": "ready",
                        "evidence": "",
                    }
                )
                writer.writerow(
                    {
                        "line_id": "scene001-0002",
                        "scene_id": "scene001",
                        "order_index": "2",
                        "speaker_name": "Murasame",
                        "voice_file": "mur100_001.ogg",
                        "jp_text": "jp-2",
                        "en_text": "Welcome home.",
                        "status": "ready",
                        "evidence": "",
                    }
                )

            (voice_root / "yos100_001.ogg").write_bytes(b"y")
            (voice_root / "mur100_001.ogg").write_bytes(b"m")

            result = prepare_single_line_poc(
                manifest.workspace_path,
                voice_root,
                speaker_name="Murasame",
                contains="welcome",
            )

            self.assertEqual(result.speaker_name, "Murasame")
            self.assertEqual(result.voice_file, "mur100_001.ogg")


if __name__ == "__main__":
    unittest.main()
