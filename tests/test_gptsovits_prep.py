from __future__ import annotations

import csv
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.cli import main
from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.gptsovits_batch import prepare_gptsovits_batch
from duolingal.core.gptsovits_prep import prepare_gptsovits_inputs
from duolingal.core.workspace import initialize_project_workspace


class GptSovitsPreparationTests(unittest.TestCase):
    def test_prepare_gptsovits_writes_train_list_and_preview_csv(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-gptsovits", projects_root=projects_root)
            project_root = projects_root / "senren-gptsovits"

            speaker_dir = project_root / "tts-dataset" / "ムラサメ"
            audio_dir = speaker_dir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / "mur001_001.ogg").write_bytes(b"ogg-data")

            with (speaker_dir / "metadata.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "line_id",
                        "scene_id",
                        "order_index",
                        "speaker_name",
                        "voice_file",
                        "audio_path",
                        "jp_text",
                        "en_text",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "line_id": "scene001-0001",
                        "scene_id": "scene001",
                        "order_index": "1",
                        "speaker_name": "ムラサメ",
                        "voice_file": "mur001_001.ogg",
                        "audio_path": "audio/mur001_001.ogg",
                        "jp_text": "「こっちだ、こっち」",
                        "en_text": "I'm over here.",
                    }
                )

            result = prepare_gptsovits_inputs(project_root, speaker_name="ムラサメ")

            self.assertEqual(result.speaker_count, 1)
            self.assertEqual(result.line_count, 1)

            train_list_path = speaker_dir / "gptsovits" / "train_ja.list"
            preview_path = speaker_dir / "gptsovits" / "preview_en.csv"

            train_lines = train_list_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(train_lines), 1)
            self.assertIn("|ムラサメ|ja|「こっちだ、こっち」", train_lines[0])
            self.assertTrue(train_lines[0].startswith(str((audio_dir / "mur001_001.ogg").resolve())))

            with preview_path.open(encoding="utf-8", newline="") as handle:
                preview_rows = list(csv.DictReader(handle))
            self.assertEqual(len(preview_rows), 1)
            self.assertEqual(preview_rows[0]["en_text"], "I'm over here.")

    def test_prepare_gptsovits_cli_outputs_summary_json(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-gptsovits-cli", projects_root=projects_root)
            project_root = projects_root / "senren-gptsovits-cli"

            speaker_dir = project_root / "tts-dataset" / "Driver"
            audio_dir = speaker_dir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / "uts001_001.ogg").write_bytes(b"ogg-data")

            with (speaker_dir / "metadata.csv").open("w", encoding="utf-8", newline="") as handle:
                handle.write(
                    "line_id,scene_id,order_index,speaker_name,voice_file,audio_path,jp_text,en_text\n"
                    "scene001-0004,scene001,4,運転手,uts001_001.ogg,audio/uts001_001.ogg,「お客さんってば」,\"Excuse me, Sir.\"\n"
                )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-gptsovits",
                        str(project_root),
                        "--speaker",
                        "運転手",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_count"], 1)
            self.assertEqual(payload["line_count"], 1)
            self.assertTrue((speaker_dir / "gptsovits" / "train_ja.list").exists())

    def test_prepare_gptsovits_batch_writes_requests_and_script(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-gptsovits-batch", projects_root=projects_root)
            project_root = projects_root / "senren-gptsovits-batch"

            speaker_dir = project_root / "tts-dataset" / "ムラサメ" / "gptsovits"
            speaker_dir.mkdir(parents=True, exist_ok=True)
            audio_dir = project_root / "tts-dataset" / "ムラサメ" / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / "mur001_001.ogg").write_bytes(b"ogg-data")
            (audio_dir / "mur001_002.ogg").write_bytes(b"ogg-data")

            with (speaker_dir / "preview_en.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["line_id", "speaker_name", "jp_text", "en_text", "audio_path"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "line_id": "scene001-0001",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「こっちだ、こっち」",
                        "en_text": "I'm over here.",
                        "audio_path": str((audio_dir / "mur001_001.ogg").resolve()),
                    }
                )
                writer.writerow(
                    {
                        "line_id": "scene001-0002",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「違うっ！」",
                        "en_text": "No!",
                        "audio_path": str((audio_dir / "mur001_002.ogg").resolve()),
                    }
                )

            result = prepare_gptsovits_batch(project_root, "ムラサメ", limit=2)
            rerun = prepare_gptsovits_batch(project_root, "ムラサメ", limit=2)

            self.assertEqual(result.item_count, 2)
            self.assertEqual(result.prompt_line_id, "scene001-0001")
            self.assertEqual(rerun.item_count, 2)
            self.assertTrue((Path(result.batch_dir) / "requests.jsonl").exists())
            script_path = Path(result.batch_dir) / "invoke_api_v2.ps1"
            self.assertTrue(script_path.exists())
            self.assertTrue(script_path.read_text(encoding="utf-8").startswith("param("))

    def test_prepare_gptsovits_batch_cli_outputs_summary_json(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-gptsovits-batch-cli", projects_root=projects_root)
            project_root = projects_root / "senren-gptsovits-batch-cli"

            speaker_dir = project_root / "tts-dataset" / "Driver" / "gptsovits"
            speaker_dir.mkdir(parents=True, exist_ok=True)
            audio_dir = project_root / "tts-dataset" / "Driver" / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / "uts001_001.ogg").write_bytes(b"ogg-data")

            with (speaker_dir / "preview_en.csv").open("w", encoding="utf-8", newline="") as handle:
                handle.write(
                    "line_id,speaker_name,jp_text,en_text,audio_path\n"
                    f"scene001-0004,運転手,「お客さんってば」,\"Excuse me, Sir.\",{(audio_dir / 'uts001_001.ogg').resolve()}\n"
                )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-gptsovits-batch",
                        str(project_root),
                        "--speaker",
                        "運転手",
                        "--limit",
                        "1",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_name"], "運転手")
            self.assertEqual(payload["item_count"], 1)
            self.assertTrue((project_root / "tts-dataset" / "Driver" / "gptsovits" / "batches" / "first-01-en" / "requests.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
