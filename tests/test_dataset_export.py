from __future__ import annotations

import csv
import unittest

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.dataset_export import export_tts_dataset
from duolingal.core.workspace import initialize_project_workspace


class DatasetExportTests(unittest.TestCase):
    def test_export_tts_dataset_groups_by_speaker(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            voice_root = temp_dir / "voice"
            voice_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-dataset", projects_root=projects_root)

            dataset_dir = projects_root / "senren-dataset" / "dataset"
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
                        "voice_file": "yos001_001.ogg",
                        "jp_text": "jp-1",
                        "en_text": "en-1",
                        "status": "ready",
                        "evidence": "",
                    }
                )
                writer.writerow(
                    {
                        "line_id": "scene001-0002",
                        "scene_id": "scene001",
                        "order_index": "2",
                        "speaker_name": "Yoshino",
                        "voice_file": "yos001_002.ogg",
                        "jp_text": "jp-2",
                        "en_text": "en-2",
                        "status": "ready",
                        "evidence": "",
                    }
                )
                writer.writerow(
                    {
                        "line_id": "scene001-0003",
                        "scene_id": "scene001",
                        "order_index": "3",
                        "speaker_name": "Murasame",
                        "voice_file": "mur001_001.ogg",
                        "jp_text": "jp-3",
                        "en_text": "en-3",
                        "status": "ready",
                        "evidence": "",
                    }
                )

            (voice_root / "yos001_001.ogg").write_bytes(b"y1")
            (voice_root / "yos001_002.ogg").write_bytes(b"y2")
            (voice_root / "mur001_001.ogg").write_bytes(b"m1")

            result = export_tts_dataset(manifest.workspace_path, voice_root, min_lines=2)

            self.assertEqual(result.speaker_count, 1)
            self.assertEqual(result.line_count, 2)
            self.assertEqual(result.speakers[0].speaker_name, "Yoshino")
            self.assertTrue((projects_root / "senren-dataset" / "tts-dataset" / "yoshino" / "audio" / "yos001_001.ogg").exists())
            self.assertTrue((projects_root / "senren-dataset" / "tts-dataset" / "yoshino" / "metadata.csv").exists())

    def test_export_tts_dataset_honors_speaker_filter(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            voice_root = temp_dir / "voice"
            voice_root.mkdir(parents=True, exist_ok=True)

            for name in ("voice.xp3", "scn.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            manifest = initialize_project_workspace(analysis, project_id="senren-dataset-filter", projects_root=projects_root)

            dataset_dir = projects_root / "senren-dataset-filter" / "dataset"
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
                        "speaker_name": "芳乃",
                        "voice_file": "yos001_001.ogg",
                        "jp_text": "jp-1",
                        "en_text": "en-1",
                        "status": "ready",
                        "evidence": "",
                    }
                )
                writer.writerow(
                    {
                        "line_id": "scene001-0002",
                        "scene_id": "scene001",
                        "order_index": "2",
                        "speaker_name": "茉子",
                        "voice_file": "mak001_001.ogg",
                        "jp_text": "jp-2",
                        "en_text": "en-2",
                        "status": "ready",
                        "evidence": "",
                    }
                )

            (voice_root / "yos001_001.ogg").write_bytes(b"y1")
            (voice_root / "mak001_001.ogg").write_bytes(b"m1")

            result = export_tts_dataset(manifest.workspace_path, voice_root, speaker_name="芳乃")

            self.assertEqual(result.speaker_count, 1)
            self.assertEqual(result.speakers[0].speaker_name, "芳乃")


if __name__ == "__main__":
    unittest.main()
