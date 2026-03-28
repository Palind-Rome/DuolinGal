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
from duolingal.core.gptsovits_production import prepare_gptsovits_production
from duolingal.core.workspace import initialize_project_workspace


class GptSovitsProductionPreparationTests(unittest.TestCase):
    def test_prepare_gptsovits_production_writes_resumable_plan(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            gpt_root = temp_dir / "tools" / "GPT-SoVITS"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            self._create_fake_gpt_root(gpt_root)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-production", projects_root=projects_root)
            project_root = projects_root / "senren-production"

            self._create_speaker_dataset(project_root, "ムラサメ", "mur001_001.ogg", "「こっちだ」", "I'm over here.")
            self._create_speaker_dataset(project_root, "芳乃", "yos001_001.ogg", "「おはよう」", "Good morning.")

            result = prepare_gptsovits_production(
                project_root,
                gpt_sovits_root=gpt_root,
                inference_limit=5,
                sync_game_root=True,
            )

            self.assertEqual(result.speaker_count, 2)
            self.assertEqual(Path(result.production_root).name, "all-cast-v1")
            self.assertTrue(Path(result.queue_path).exists())
            self.assertTrue(Path(result.run_script_path).exists())
            self.assertTrue(Path(result.readme_path).exists())

            queue_payload = json.loads(Path(result.queue_path).read_text(encoding="utf-8"))
            self.assertEqual(queue_payload["gpt_sovits_root"], str(gpt_root.resolve()))
            self.assertEqual(queue_payload["sync_game_root"], True)
            self.assertEqual(len(queue_payload["speakers"]), 2)
            self.assertEqual(queue_payload["speakers"][0]["batch_limit"], 1)

            run_script_text = Path(result.run_script_path).read_text(encoding="utf-8")
            self.assertIn("run-gptsovits-production", run_script_text)
            self.assertIn("Set-Location", run_script_text)
            self.assertIn(str(project_root.parents[2] / "src"), run_script_text)

            readme_text = Path(result.readme_path).read_text(encoding="utf-8")
            self.assertIn("夜间量产计划", readme_text)
            self.assertIn("前处理 -> GPT -> SoVITS", readme_text)

    def test_prepare_gptsovits_production_cli_outputs_summary_json(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            gpt_root = temp_dir / "tools" / "GPT-SoVITS"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            self._create_fake_gpt_root(gpt_root)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-production-cli", projects_root=projects_root)
            project_root = projects_root / "senren-production-cli"

            self._create_speaker_dataset(project_root, "運転手", "uts001_001.ogg", "「お客さんってば」", "Excuse me, Sir.")

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-gptsovits-production",
                        str(project_root),
                        "--speaker",
                        "運転手",
                        "--gpt-sovits-root",
                        str(gpt_root),
                        "--sync-game-root",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_count"], 1)
            self.assertEqual(payload["sync_game_root"], True)
            self.assertTrue(Path(payload["run_script_path"]).exists())

    def _create_speaker_dataset(
        self,
        project_root: Path,
        speaker_name: str,
        voice_file: str,
        jp_text: str,
        en_text: str,
    ) -> None:
        speaker_dir = project_root / "tts-dataset" / speaker_name
        audio_dir = speaker_dir / "audio"
        preview_dir = speaker_dir / "gptsovits"
        audio_dir.mkdir(parents=True, exist_ok=True)
        preview_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / voice_file
        audio_path.write_bytes(b"ogg-data")

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
                    "speaker_name": speaker_name,
                    "voice_file": voice_file,
                    "audio_path": f"audio/{voice_file}",
                    "jp_text": jp_text,
                    "en_text": en_text,
                }
            )

        with (preview_dir / "preview_en.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["line_id", "speaker_name", "jp_text", "en_text", "audio_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "line_id": "scene001-0001",
                    "speaker_name": speaker_name,
                    "jp_text": jp_text,
                    "en_text": en_text,
                    "audio_path": str(audio_path.resolve()),
                }
            )

    def _create_fake_gpt_root(self, gpt_root: Path) -> None:
        for relative_file in (
            "GPT_SoVITS/prepare_datasets/1-get-text.py",
            "GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
            "GPT_SoVITS/prepare_datasets/3-get-semantic.py",
            "GPT_SoVITS/s1_train.py",
            "GPT_SoVITS/s2_train.py",
            "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
            "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth",
            "GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2D2333k.pth",
        ):
            touch(gpt_root / relative_file)

        (gpt_root / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large").mkdir(
            parents=True, exist_ok=True
        )
        (gpt_root / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base").mkdir(
            parents=True, exist_ok=True
        )


if __name__ == "__main__":
    unittest.main()
