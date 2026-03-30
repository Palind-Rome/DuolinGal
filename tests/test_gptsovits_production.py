from __future__ import annotations

import csv
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from support import ensure_src_on_path, temporary_workspace, touch

ensure_src_on_path()

from duolingal.cli import main
from duolingal.core.analyzer import analyze_game_directory
from duolingal.core.final_cleanup import prepare_final_cleanup
from duolingal.core.gptsovits_production import _synthesize_batch, prepare_gptsovits_production
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

    def test_prepare_gptsovits_production_applies_overrides(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"
            gpt_root = temp_dir / "tools" / "GPT-SoVITS"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            self._create_fake_gpt_root(gpt_root)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-production-overrides", projects_root=projects_root)
            project_root = projects_root / "senren-production-overrides"

            self._create_speaker_dataset(project_root, "レナ", "len001_001.ogg", "「こんにちは」", "Hello.")
            self._create_speaker_dataset(project_root, "廉太郎", "ren001_001.ogg", "「よう」", "Yo.")
            self._create_speaker_dataset(project_root, "白狛", "srk001_001.ogg", "「グルル」", "Grr.")

            overrides_dir = project_root / "tts-production"
            overrides_dir.mkdir(parents=True, exist_ok=True)
            (overrides_dir / "production-overrides.json").write_text(
                json.dumps(
                    {
                        "exclude_speakers": ["白狛"],
                        "speaker_prompt_line_ids": {
                            "レナ": "006・レナ登場ver1.03.ks-0436",
                            "廉太郎": "001・アーサー王ver1.07.ks-0346",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
                newline="\n",
            )

            result = prepare_gptsovits_production(
                project_root,
                gpt_sovits_root=gpt_root,
                inference_limit=5,
            )

            queue_payload = json.loads(Path(result.queue_path).read_text(encoding="utf-8"))
            speaker_names = [item["speaker_name"] for item in queue_payload["speakers"]]
            self.assertEqual(speaker_names, ["レナ", "廉太郎"])

            prompt_line_ids = {item["speaker_name"]: item.get("prompt_line_id") for item in queue_payload["speakers"]}
            self.assertEqual(prompt_line_ids["レナ"], "006・レナ登場ver1.03.ks-0436")
            self.assertEqual(prompt_line_ids["廉太郎"], "001・アーサー王ver1.07.ks-0346")

    def test_synthesize_batch_skips_invalid_text_http_errors(self) -> None:
        with temporary_workspace() as temp_dir:
            batch_dir = temp_dir / "batch"
            output_dir = batch_dir / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)

            requests = [
                {
                    "line_id": "scene001-0001",
                    "output_file_name": "ok.wav",
                    "request": {"text": "Hello there."},
                },
                {
                    "line_id": "scene001-0002",
                    "output_file_name": "skip.wav",
                    "request": {"text": "......"},
                },
            ]
            (batch_dir / "requests.jsonl").write_text(
                "\n".join(json.dumps(item, ensure_ascii=False) for item in requests) + "\n",
                encoding="utf-8",
            )

            class _FakeResponse:
                def __init__(self, payload: bytes) -> None:
                    self.status = 200
                    self._payload = payload

                def read(self) -> bytes:
                    return self._payload

                def __enter__(self) -> "_FakeResponse":
                    return self

                def __exit__(self, exc_type, exc, tb) -> None:
                    return None

            def fake_urlopen(request, timeout=600):  # type: ignore[no-untyped-def]
                body = json.loads(request.data.decode("utf-8"))
                if body["text"] == "......":
                    raise HTTPError(
                        request.full_url,
                        400,
                        "Bad Request",
                        hdrs=None,
                        fp=io.BytesIO(b'{"message":"tts failed","Exception":"\xe8\xaf\xb7\xe8\xbe\x93\xe5\x85\xa5\xe6\x9c\x89\xe6\x95\x88\xe6\x96\x87\xe6\x9c\xac"}'),
                    )
                return _FakeResponse(b"wav-data")

            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                skipped = _synthesize_batch(batch_dir, 9880)

            self.assertEqual(skipped, {"skip.wav"})
            self.assertEqual((output_dir / "ok.wav").read_bytes(), b"wav-data")
            self.assertFalse((output_dir / "skip.wav").exists())
            skipped_log = (batch_dir / "skipped-invalid-tts.jsonl").read_text(encoding="utf-8")
            self.assertIn("skip.wav", skipped_log)

    def test_prepare_final_cleanup_creates_safe_copy_and_review_sheet(self) -> None:
        with temporary_workspace() as temp_dir:
            game_root = temp_dir / "game"
            projects_root = temp_dir / "projects"

            for name in ("voice.xp3", "scn.xp3", "patch.xp3", "KAGParserEx.dll", "psbfile.dll", "senrenbanka.exe"):
                touch(game_root / name)

            analysis = analyze_game_directory(game_root)
            initialize_project_workspace(analysis, project_id="senren-final-cleanup", projects_root=projects_root)
            project_root = projects_root / "senren-final-cleanup"

            production_root = project_root / "tts-production" / "all-cast-v1"
            override_root = production_root / "game-ready" / "unencrypted"
            override_root.mkdir(parents=True, exist_ok=True)
            (override_root / "weak001.ogg").write_bytes(b"weak")
            (override_root / "scene001_001.ogg").write_bytes(b"ok")
            temp_artifact = override_root / ".gptsovits-ogg-temp"
            temp_artifact.mkdir()
            (temp_artifact / "input.wav").write_bytes(b"temp")

            batch_dir = project_root / "tts-dataset" / "芳乃" / "gptsovits" / "batches" / "first-2-en"
            batch_dir.mkdir(parents=True, exist_ok=True)
            with (batch_dir / "requests.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "order_index",
                        "line_id",
                        "voice_file",
                        "source_audio_path",
                        "jp_text",
                        "en_text",
                        "prompt_line_id",
                        "prompt_audio_path",
                        "prompt_text",
                        "prompt_source",
                        "output_file_name",
                        "output_path",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "order_index": "1",
                        "line_id": "scene001-0001",
                        "voice_file": "weak001.ogg",
                        "source_audio_path": "",
                        "jp_text": "「ふん」",
                        "en_text": "Hmph.",
                        "prompt_line_id": "scene001-0001",
                        "prompt_audio_path": "",
                        "prompt_text": "「ふん」",
                        "prompt_source": "self",
                        "output_file_name": "weak001.wav",
                        "output_path": "",
                    }
                )
                writer.writerow(
                    {
                        "order_index": "2",
                        "line_id": "scene001-0002",
                        "voice_file": "scene001_001.ogg",
                        "source_audio_path": "",
                        "jp_text": "「おはよう」",
                        "en_text": "Good morning.",
                        "prompt_line_id": "scene001-0002",
                        "prompt_audio_path": "",
                        "prompt_text": "「おはよう」",
                        "prompt_source": "self",
                        "output_file_name": "scene001_001.wav",
                        "output_path": "",
                    }
                )

            state_payload = {
                "completed_speakers": [
                    {
                        "speaker_name": "芳乃",
                        "experiment_name": "yos-v2",
                        "batch_dir": str(batch_dir),
                        "generated_count": 2,
                        "converted_count": 2,
                        "gpt_weight_path": "gpt.ckpt",
                        "sovits_weight_path": "sovits.pth",
                    }
                ]
            }
            (production_root / "production-state.json").write_text(
                json.dumps(state_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
                newline="\n",
            )

            result = prepare_final_cleanup(project_root)

            cleanup_root = Path(result.cleanup_root)
            copied_root = cleanup_root / "source" / "unencrypted"
            self.assertTrue((copied_root / "weak001.ogg").exists())
            self.assertTrue((copied_root / "scene001_001.ogg").exists())
            self.assertFalse((copied_root / ".gptsovits-ogg-temp").exists())

            review_sheet = (cleanup_root / "review" / "cleanup-review.csv").read_text(encoding="utf-8")
            self.assertIn("weak001.ogg", review_sheet)
            self.assertIn("english_interjection_only", review_sheet)
            self.assertIn("jp_short_reaction", review_sheet)
            self.assertNotIn("scene001_001.ogg,Good morning.", review_sheet)

            apply_script = (cleanup_root / "scripts" / "apply-reviewed-removals.ps1").read_text(encoding="utf-8")
            self.assertIn("cleanup-review.csv", apply_script)
            rebuild_script = (cleanup_root / "scripts" / "rebuild-patch-from-clean-copy.ps1").read_text(encoding="utf-8")
            self.assertIn(str(Path(__file__).resolve().parents[1]), rebuild_script)

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
