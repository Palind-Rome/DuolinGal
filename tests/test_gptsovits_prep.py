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
            project_root, speaker_dir, audio_dir = self._create_project_with_dataset(
                temp_dir,
                project_id="senren-gptsovits",
                speaker_name="ムラサメ",
                rows=[
                    {
                        "line_id": "scene001-0001",
                        "scene_id": "scene001",
                        "order_index": "1",
                        "speaker_name": "ムラサメ",
                        "voice_file": "mur001_001.ogg",
                        "audio_path": "audio/mur001_001.ogg",
                        "jp_text": "「ここです、ここです。」",
                        "en_text": "I'm over here.",
                    }
                ],
            )

            result = prepare_gptsovits_inputs(project_root, speaker_name="ムラサメ")

            self.assertEqual(result.speaker_count, 1)
            self.assertEqual(result.line_count, 1)

            train_list_path = speaker_dir / "gptsovits" / "train_ja.list"
            preview_path = speaker_dir / "gptsovits" / "preview_en.csv"

            train_lines = train_list_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(train_lines), 1)
            self.assertIn("|ムラサメ|ja|「ここです、ここです。」", train_lines[0])
            self.assertTrue(train_lines[0].startswith(str((audio_dir / "mur001_001.ogg").resolve())))

            with preview_path.open(encoding="utf-8", newline="") as handle:
                preview_rows = list(csv.DictReader(handle))
            self.assertEqual(len(preview_rows), 1)
            self.assertEqual(preview_rows[0]["en_text"], "I'm over here.")

    def test_prepare_gptsovits_cli_outputs_summary_json(self) -> None:
        with temporary_workspace() as temp_dir:
            project_root, speaker_dir, _ = self._create_project_with_dataset(
                temp_dir,
                project_id="senren-gptsovits-cli",
                speaker_name="Driver",
                rows=[
                    {
                        "line_id": "scene001-0004",
                        "scene_id": "scene001",
                        "order_index": "4",
                        "speaker_name": "Driver",
                        "voice_file": "uts001_001.ogg",
                        "audio_path": "audio/uts001_001.ogg",
                        "jp_text": "「お客さんってぇ。」",
                        "en_text": "Excuse me, Sir.",
                    }
                ],
            )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-gptsovits",
                        str(project_root),
                        "--speaker",
                        "Driver",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_count"], 1)
            self.assertEqual(payload["line_count"], 1)
            self.assertTrue((speaker_dir / "gptsovits" / "train_ja.list").exists())

    def test_prepare_gptsovits_batch_anchor_mode_writes_requests_and_script(self) -> None:
        with temporary_workspace() as temp_dir:
            project_root, _, _ = self._create_project_with_preview(
                temp_dir,
                project_id="senren-gptsovits-batch",
                speaker_name="ムラサメ",
                rows=[
                    {
                        "line_id": "scene001-0001",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「ここです、ここです。」",
                        "en_text": "I'm over here.",
                        "audio_name": "mur001_001.ogg",
                    },
                    {
                        "line_id": "scene001-0002",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「違った！」",
                        "en_text": "No!",
                        "audio_name": "mur001_002.ogg",
                    },
                ],
            )

            result = prepare_gptsovits_batch(project_root, "ムラサメ", limit=2)

            self.assertEqual(result.item_count, 2)
            self.assertEqual(result.reference_mode, "anchor")
            self.assertEqual(result.prompt_line_id, "scene001-0001")
            self.assertTrue((Path(result.batch_dir) / "requests.jsonl").exists())
            script_path = Path(result.batch_dir) / "invoke_api_v2.ps1"
            self.assertTrue(script_path.exists())
            self.assertTrue(script_path.read_text(encoding="utf-8").startswith("param("))

            requests = self._read_requests_jsonl(Path(result.batch_dir) / "requests.jsonl")
            self.assertEqual(requests[0]["request"]["prompt_text"], "「ここです、ここです。」")
            self.assertEqual(requests[1]["request"]["prompt_text"], "「ここです、ここです。」")

    def test_prepare_gptsovits_batch_per_line_mode_uses_each_rows_prompt(self) -> None:
        with temporary_workspace() as temp_dir:
            project_root, _, audio_dir = self._create_project_with_preview(
                temp_dir,
                project_id="senren-gptsovits-batch-self",
                speaker_name="ムラサメ",
                rows=[
                    {
                        "line_id": "scene001-0001",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「ここです、ここです。」",
                        "en_text": "I'm over here.",
                        "audio_name": "mur001_001.ogg",
                    },
                    {
                        "line_id": "scene001-0002",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「違った！」",
                        "en_text": "No!",
                        "audio_name": "mur001_002.ogg",
                    },
                ],
            )

            result = prepare_gptsovits_batch(project_root, "ムラサメ", limit=2, reference_mode="per-line")

            self.assertEqual(result.reference_mode, "per-line")
            self.assertEqual(result.items[0].prompt_source, "self")
            self.assertEqual(result.items[1].prompt_source, "self")
            self.assertEqual(result.items[1].prompt_line_id, "scene001-0002")
            self.assertEqual(result.items[1].prompt_audio_path, str((audio_dir / "mur001_002.ogg").resolve()))

            requests = self._read_requests_jsonl(Path(result.batch_dir) / "requests.jsonl")
            self.assertEqual(requests[1]["request"]["prompt_text"], "「違った！」")

    def test_prepare_gptsovits_batch_auto_mode_falls_back_for_short_interjections(self) -> None:
        with temporary_workspace() as temp_dir:
            project_root, _, audio_dir = self._create_project_with_preview(
                temp_dir,
                project_id="senren-gptsovits-batch-auto",
                speaker_name="ムラサメ",
                rows=[
                    {
                        "line_id": "scene001-0001",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「ふむ。お主が、吾輩のご主人か？」",
                        "en_text": "Hmm. So you are my master?",
                        "audio_name": "mur001_001.ogg",
                    },
                    {
                        "line_id": "scene001-0002",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「えっ？」",
                        "en_text": "Huh?",
                        "audio_name": "mur001_002.ogg",
                    },
                    {
                        "line_id": "scene001-0003",
                        "speaker_name": "ムラサメ",
                        "jp_text": "「そこにいるなら、返事をせぬか。」",
                        "en_text": "If you are there, answer me.",
                        "audio_name": "mur001_003.ogg",
                    },
                ],
            )

            result = prepare_gptsovits_batch(project_root, "ムラサメ", limit=3, reference_mode="auto")

            self.assertEqual(result.reference_mode, "auto")
            self.assertEqual(result.items[0].prompt_source, "self")
            self.assertEqual(result.items[1].prompt_source, "anchor-fallback")
            self.assertEqual(result.items[1].prompt_line_id, "scene001-0001")
            self.assertEqual(result.items[1].prompt_audio_path, str((audio_dir / "mur001_001.ogg").resolve()))
            self.assertEqual(result.items[2].prompt_source, "self")
            self.assertEqual(result.items[2].prompt_line_id, "scene001-0003")

            with (Path(result.batch_dir) / "requests.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[1]["prompt_source"], "anchor-fallback")
            self.assertEqual(rows[2]["prompt_source"], "self")

    def test_prepare_gptsovits_batch_cli_outputs_reference_mode(self) -> None:
        with temporary_workspace() as temp_dir:
            project_root, _, _ = self._create_project_with_preview(
                temp_dir,
                project_id="senren-gptsovits-batch-cli",
                speaker_name="Driver",
                rows=[
                    {
                        "line_id": "scene001-0004",
                        "speaker_name": "Driver",
                        "jp_text": "「お客さんってぇ。」",
                        "en_text": "Excuse me, Sir.",
                        "audio_name": "uts001_001.ogg",
                    }
                ],
            )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-gptsovits-batch",
                        str(project_root),
                        "--speaker",
                        "Driver",
                        "--limit",
                        "1",
                        "--reference-mode",
                        "auto",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_name"], "Driver")
            self.assertEqual(payload["item_count"], 1)
            self.assertEqual(payload["reference_mode"], "auto")
            self.assertTrue((project_root / "tts-dataset" / "Driver" / "gptsovits" / "batches" / "first-01-en" / "requests.jsonl").exists())

    def _create_project_with_dataset(
        self,
        temp_dir: Path,
        *,
        project_id: str,
        speaker_name: str,
        rows: list[dict[str, str]],
    ) -> tuple[Path, Path, Path]:
        game_root = temp_dir / "game"
        projects_root = temp_dir / "projects"

        for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
            touch(game_root / name)

        analysis = analyze_game_directory(game_root)
        initialize_project_workspace(analysis, project_id=project_id, projects_root=projects_root)
        project_root = projects_root / project_id

        speaker_dir = project_root / "tts-dataset" / speaker_name
        audio_dir = speaker_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        for row in rows:
            (audio_dir / row["voice_file"]).write_bytes(b"ogg-data")

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
            for row in rows:
                writer.writerow(row)

        return project_root, speaker_dir, audio_dir

    def _create_project_with_preview(
        self,
        temp_dir: Path,
        *,
        project_id: str,
        speaker_name: str,
        rows: list[dict[str, str]],
    ) -> tuple[Path, Path, Path]:
        game_root = temp_dir / "game"
        projects_root = temp_dir / "projects"

        for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
            touch(game_root / name)

        analysis = analyze_game_directory(game_root)
        initialize_project_workspace(analysis, project_id=project_id, projects_root=projects_root)
        project_root = projects_root / project_id

        speaker_root = project_root / "tts-dataset" / speaker_name
        preview_dir = speaker_root / "gptsovits"
        audio_dir = speaker_root / "audio"
        preview_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        preview_path = preview_dir / "preview_en.csv"
        with preview_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["line_id", "speaker_name", "jp_text", "en_text", "audio_path"],
            )
            writer.writeheader()
            for row in rows:
                audio_path = audio_dir / row["audio_name"]
                audio_path.write_bytes(b"ogg-data")
                writer.writerow(
                    {
                        "line_id": row["line_id"],
                        "speaker_name": row["speaker_name"],
                        "jp_text": row["jp_text"],
                        "en_text": row["en_text"],
                        "audio_path": str(audio_path.resolve()),
                    }
                )

        return project_root, preview_dir, audio_dir

    def _read_requests_jsonl(self, path: Path) -> list[dict[str, object]]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
