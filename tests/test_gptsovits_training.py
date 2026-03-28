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
from duolingal.core.gptsovits_training import prepare_gptsovits_training
from duolingal.core.workspace import initialize_project_workspace


class GptSovitsTrainingPreparationTests(unittest.TestCase):
    def test_prepare_gptsovits_training_writes_workspace_and_scripts(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            gpt_root = temp_dir / "tools" / "GPT-SoVITS"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            self._create_fake_gpt_root(gpt_root)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-train", projects_root=projects_root)
            project_root = projects_root / "senren-train"

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

            result = prepare_gptsovits_training(
                project_root,
                "ムラサメ",
                gpt_sovits_root=gpt_root,
            )

            self.assertEqual(result.speaker_name, "ムラサメ")
            self.assertEqual(result.speaker_alias, "mur_v2")
            self.assertEqual(result.experiment_name, "mur-v2")
            self.assertEqual(result.line_count, 1)
            self.assertIn("tts-training", result.source_audio_root)
            self.assertTrue((Path(result.source_audio_root) / "mur001_001.ogg").exists())

            input_list_path = Path(result.input_list_path)
            self.assertTrue(input_list_path.exists())
            input_line = input_list_path.read_text(encoding="utf-8").strip()
            self.assertEqual(input_line, "mur001_001.ogg|mur_v2|ja|「こっちだ、こっち」")

            prepare_all_script = Path(result.prepare_all_script_path)
            self.assertTrue(prepare_all_script.exists())
            self.assertIn("run-prepare-stage1.ps1", prepare_all_script.read_text(encoding="utf-8"))

            prepare_stage1_script_text = Path(result.prepare_stage1_script_path).read_text(encoding="utf-8")
            self.assertIn("CONDA_PREFIX", prepare_stage1_script_text)
            self.assertIn("python.exe", prepare_stage1_script_text)
            self.assertIn("PYTHONPATH", prepare_stage1_script_text)

            prepare_stage3_script_text = Path(result.prepare_stage3_script_path).read_text(encoding="utf-8")
            self.assertIn("s2config.stage3.json", prepare_stage3_script_text)
            self.assertIn("Properties.Remove('version')", prepare_stage3_script_text)
            self.assertIn("UTF8Encoding($false)", prepare_stage3_script_text)
            self.assertIn('@("item_name`tsemantic_audio")', prepare_stage3_script_text)

            train_gpt_script_text = Path(result.train_gpt_script_path).read_text(encoding="utf-8")
            self.assertIn("train-gpt-launcher.py", train_gpt_script_text)

            train_gpt_launcher_path = Path(result.train_gpt_script_path).with_name("train-gpt-launcher.py")
            self.assertTrue(train_gpt_launcher_path.exists())
            train_gpt_launcher_text = train_gpt_launcher_path.read_text(encoding="utf-8")
            self.assertIn('devices=1 if torch.cuda.is_available() else 1', train_gpt_launcher_text)
            self.assertIn('strategy="auto"', train_gpt_launcher_text)
            self.assertIn("enable_progress_bar=False", train_gpt_launcher_text)
            self.assertIn("num_replicas=1, rank=0", train_gpt_launcher_text)
            self.assertIn("STEP_LOG_INTERVAL = 50", train_gpt_launcher_text)
            self.assertIn('print(f"Epoch {trainer.current_epoch + 1}/{trainer.max_epochs} started")', train_gpt_launcher_text)
            self.assertIn('print(" | ".join(parts))', train_gpt_launcher_text)

            gpt_config_text = Path(result.gpt_config_path).read_text(encoding="utf-8")
            self.assertIn("pretrained_s1", gpt_config_text)
            self.assertIn("mur-v2", gpt_config_text)

            sovits_config = json.loads(Path(result.sovits_config_path).read_text(encoding="utf-8"))
            self.assertEqual(sovits_config["train"]["pretrained_s2G"].split("\\")[-1], "s2G2333k.pth")
            self.assertEqual(sovits_config["train"]["gpu_numbers"], "0")

    def test_prepare_gptsovits_training_cli_outputs_summary_json(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            gpt_root = temp_dir / "tools" / "GPT-SoVITS"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            self._create_fake_gpt_root(gpt_root)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-train-cli", projects_root=projects_root)
            project_root = projects_root / "senren-train-cli"

            speaker_dir = project_root / "tts-dataset" / "Driver"
            audio_dir = speaker_dir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / "uts001_001.ogg").write_bytes(b"ogg-data")

            with (speaker_dir / "metadata.csv").open("w", encoding="utf-8", newline="") as handle:
                handle.write(
                    "line_id,scene_id,order_index,speaker_name,voice_file,audio_path,jp_text,en_text\n"
                    'scene001-0004,scene001,4,運転手,uts001_001.ogg,audio/uts001_001.ogg,「お客さんってば」,"Excuse me, Sir."\n'
                )

            command_stdout = io.StringIO()
            with redirect_stdout(command_stdout):
                exit_code = main(
                    [
                        "prepare-gptsovits-train",
                        str(project_root),
                        "--speaker",
                        "運転手",
                        "--gpt-sovits-root",
                        str(gpt_root),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(command_stdout.getvalue())
            self.assertEqual(payload["speaker_name"], "運転手")
            self.assertEqual(payload["speaker_alias"], "uts_v2")
            self.assertTrue(Path(payload["train_gpt_script_path"]).exists())

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
