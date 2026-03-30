from __future__ import annotations

import argparse
import json

from duolingal.domain.models import PreflightStage
from duolingal.services.project_service import ProjectService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="duolingal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a game installation directory.")
    analyze_parser.add_argument("game_path", help="Game installation directory.")

    init_parser = subparsers.add_parser("init-project", help="Initialize a project workspace.")
    init_parser.add_argument("game_path", help="Game installation directory.")
    init_parser.add_argument("--project-id", help="Optional project identifier override.")

    tools_parser = subparsers.add_parser("list-tools", help="List external tool requirements and detection results.")
    tools_parser.add_argument("--config", help="Optional toolchain config path.")

    extract_parser = subparsers.add_parser("extract", help="Extract configured resource packages with an offline tool.")
    extract_parser.add_argument("project_root", help="Initialized project workspace.")
    extract_parser.add_argument("--config", help="Toolchain config path.")
    extract_parser.add_argument("--package", dest="packages", action="append", help="Specific resource package to extract.")

    decompile_parser = subparsers.add_parser("decompile-scripts", help="Decompile SCN or PSB assets into JSON.")
    decompile_parser.add_argument("project_root", help="Initialized project workspace.")
    decompile_parser.add_argument("--config", help="Toolchain config path.")
    decompile_parser.add_argument("--input-root", help="Optional source asset root.")
    decompile_parser.add_argument("--output-root", help="Optional JSON output root.")

    krkrdump_parser = subparsers.add_parser(
        "prepare-krkrdump",
        help="Generate KrkrDump.json and print the local launch command.",
    )
    krkrdump_parser.add_argument("project_root", help="Initialized project workspace.")
    krkrdump_parser.add_argument("--config", help="Toolchain config path.")
    krkrdump_parser.add_argument("--output-root", help="Optional override for KrkrDump output directory.")

    preflight_parser = subparsers.add_parser("preflight", help="Check whether the project is ready for the next stage.")
    preflight_parser.add_argument("project_root", help="Initialized project workspace.")
    preflight_parser.add_argument("--config", help="Toolchain config path.")
    preflight_parser.add_argument(
        "--stage",
        choices=[stage.value for stage in PreflightStage],
        default=PreflightStage.BUILD_LINES.value,
        help="Target stage to validate.",
    )

    lines_parser = subparsers.add_parser("build-lines", help="Build lines.csv from script JSON.")
    lines_parser.add_argument("project_root", help="Initialized project workspace.")
    lines_parser.add_argument("--script-root", help="Optional script JSON root.")

    poc_parser = subparsers.add_parser("prepare-poc", help="Prepare a single-line all-ages voice replacement PoC.")
    poc_parser.add_argument("project_root", help="Initialized project workspace.")
    poc_parser.add_argument("voice_root", help="Extracted voice directory used for source lookup.")
    poc_parser.add_argument("--line-id", help="Optional exact line_id from lines.csv.")
    poc_parser.add_argument("--speaker", help="Optional exact speaker_name filter.")
    poc_parser.add_argument("--contains", help="Optional substring filter across speaker, JP, and EN text.")

    patch_parser = subparsers.add_parser("prepare-patch", help="Prepare a patch staging directory from an override tree.")
    patch_parser.add_argument("project_root", help="Initialized project workspace.")
    patch_parser.add_argument("source_root", help="Override tree to copy into the patch archive staging directory.")
    patch_parser.add_argument("--archive-name", help="Optional archive name override, such as patch2.")

    dataset_parser = subparsers.add_parser("export-dataset", help="Export a per-speaker TTS dataset from lines.csv and voice files.")
    dataset_parser.add_argument("project_root", help="Initialized project workspace.")
    dataset_parser.add_argument("voice_root", help="Extracted voice directory used for audio file lookup.")
    dataset_parser.add_argument("--speaker", help="Optional exact speaker_name filter.")
    dataset_parser.add_argument("--min-lines", type=int, default=1, help="Minimum line count required to keep a speaker.")

    gptsovits_parser = subparsers.add_parser(
        "prepare-gptsovits",
        help="Prepare GPT-SoVITS training lists from exported speaker datasets.",
    )
    gptsovits_parser.add_argument("project_root", help="Initialized project workspace.")
    gptsovits_parser.add_argument("--dataset-root", help="Optional existing tts-dataset root override.")
    gptsovits_parser.add_argument("--speaker", help="Optional exact speaker_name filter.")

    gptsovits_batch_parser = subparsers.add_parser(
        "prepare-gptsovits-batch",
        help="Prepare a small English synthesis batch for GPT-SoVITS api_v2.",
    )
    gptsovits_batch_parser.add_argument("project_root", help="Initialized project workspace.")
    gptsovits_batch_parser.add_argument("--speaker", required=True, help="Exact speaker_name to prepare.")
    gptsovits_batch_parser.add_argument("--limit", type=int, default=10, help="How many English lines to stage.")
    gptsovits_batch_parser.add_argument("--prompt-line-id", help="Optional line_id to force as the reference prompt.")
    gptsovits_batch_parser.add_argument(
        "--reference-mode",
        choices=["anchor", "per-line", "auto"],
        default="anchor",
        help="How GPT-SoVITS reference audio/text should be chosen for each target line.",
    )

    gptsovits_reinject_parser = subparsers.add_parser(
        "prepare-gptsovits-reinject",
        help="Convert one GPT-SoVITS batch output into a game-ready OGG override and patch staging.",
    )
    gptsovits_reinject_parser.add_argument("project_root", help="Initialized project workspace.")
    gptsovits_reinject_parser.add_argument("batch_dir", help="GPT-SoVITS batch directory that contains outputs/ and requests.csv.")
    gptsovits_reinject_parser.add_argument("--target-voice-file", required=True, help="Target game voice file name, such as uts001_001.ogg.")
    gptsovits_reinject_parser.add_argument("--source-output-name", help="Optional synthesized WAV file name, such as mur001_001.wav.")
    gptsovits_reinject_parser.add_argument("--target-sample-rate", type=int, default=48000, help="Target OGG sample rate for the game-ready output.")
    gptsovits_reinject_parser.add_argument("--archive-name", help="Optional patch archive name override, such as patch2.")

    gptsovits_reinject_batch_parser = subparsers.add_parser(
        "prepare-gptsovits-reinject-batch",
        help="Convert a GPT-SoVITS batch output directory into a game-ready OGG override tree and patch staging.",
    )
    gptsovits_reinject_batch_parser.add_argument("project_root", help="Initialized project workspace.")
    gptsovits_reinject_batch_parser.add_argument("batch_dir", help="GPT-SoVITS batch directory that contains outputs/ and requests.csv.")
    gptsovits_reinject_batch_parser.add_argument("--limit", type=int, help="Optional maximum number of batch rows to convert.")
    gptsovits_reinject_batch_parser.add_argument("--target-sample-rate", type=int, default=48000, help="Target OGG sample rate for the game-ready outputs.")
    gptsovits_reinject_batch_parser.add_argument("--archive-name", help="Optional patch archive name override, such as patch2.")

    gptsovits_train_parser = subparsers.add_parser(
        "prepare-gptsovits-train",
        help="Prepare an official GPT-SoVITS training workspace for one speaker.",
    )
    gptsovits_train_parser.add_argument("project_root", help="Initialized project workspace.")
    gptsovits_train_parser.add_argument("--speaker", required=True, help="Exact speaker_name to prepare.")
    gptsovits_train_parser.add_argument("--gpt-sovits-root", help="Optional local GPT-SoVITS repository root override.")
    gptsovits_train_parser.add_argument("--version", choices=["v2"], default="v2", help="Official GPT-SoVITS model family to target.")
    gptsovits_train_parser.add_argument("--gpu", default="0", help="GPU index string, such as 0.")
    gptsovits_train_parser.add_argument("--full-precision", action="store_true", help="Disable half precision in generated training scripts.")
    gptsovits_train_parser.add_argument("--gpt-epochs", type=int, default=12, help="GPT stage epoch count for the generated config.")
    gptsovits_train_parser.add_argument("--sovits-epochs", type=int, default=6, help="SoVITS stage epoch count for the generated config.")
    gptsovits_train_parser.add_argument("--gpt-batch-size", type=int, default=4, help="GPT stage batch size for the generated config.")
    gptsovits_train_parser.add_argument("--sovits-batch-size", type=int, default=4, help="SoVITS stage batch size for the generated config.")

    gptsovits_production_parser = subparsers.add_parser(
        "prepare-gptsovits-production",
        help="Prepare a resumable GPT-SoVITS training and inference queue for multiple speakers.",
    )
    gptsovits_production_parser.add_argument("project_root", help="Initialized project workspace.")
    gptsovits_production_parser.add_argument("--speaker", dest="speakers", action="append", help="Optional exact speaker_name filter. Repeat to enqueue more than one role.")
    gptsovits_production_parser.add_argument("--min-lines", type=int, default=1, help="Minimum aligned line count required to keep a speaker in the queue.")
    gptsovits_production_parser.add_argument("--gpt-sovits-root", help="Optional local GPT-SoVITS repository root override.")
    gptsovits_production_parser.add_argument("--reference-mode", choices=["anchor", "per-line", "auto"], default="auto", help="How GPT-SoVITS reference audio/text should be chosen during overnight inference.")
    gptsovits_production_parser.add_argument("--inference-limit", type=int, help="Optional per-speaker cap for how many English preview lines to synthesize.")
    gptsovits_production_parser.add_argument("--target-sample-rate", type=int, default=48000, help="Target OGG sample rate for the combined game-ready outputs.")
    gptsovits_production_parser.add_argument("--api-port", type=int, default=9880, help="Local GPT-SoVITS api_v2 port.")
    gptsovits_production_parser.add_argument("--sync-game-root", action="store_true", help="Copy completed OGG overrides into the real game root's unencrypted directory at the end of the queue.")
    gptsovits_production_parser.add_argument("--gpt-epochs", type=int, default=12, help="GPT stage epoch count for each generated training workspace.")
    gptsovits_production_parser.add_argument("--sovits-epochs", type=int, default=6, help="SoVITS stage epoch count for each generated training workspace.")
    gptsovits_production_parser.add_argument("--gpt-batch-size", type=int, default=4, help="GPT stage batch size for each generated training workspace.")
    gptsovits_production_parser.add_argument("--sovits-batch-size", type=int, default=4, help="SoVITS stage batch size for each generated training workspace.")

    gptsovits_production_run_parser = subparsers.add_parser(
        "run-gptsovits-production",
        help="Run a previously prepared GPT-SoVITS production queue.",
    )
    gptsovits_production_run_parser.add_argument("production_root", help="Prepared tts-production/<plan> directory.")

    final_cleanup_parser = subparsers.add_parser(
        "prepare-final-cleanup",
        help="Create a safe cleanup copy and review sheets for final weak-utterance pruning.",
    )
    final_cleanup_parser.add_argument("project_root", help="Initialized project workspace.")
    final_cleanup_parser.add_argument("--production-name", default="all-cast-v1", help="Which prepared production plan to copy from.")
    final_cleanup_parser.add_argument("--cleanup-name", default="final-cleanup-v1", help="Name of the generated cleanup workspace.")

    args = parser.parse_args(argv)
    service = ProjectService()

    if args.command == "analyze":
        analysis = service.analyze(args.game_path)
        _emit_json(analysis.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "init-project":
        manifest = service.init_project(args.game_path, project_id=args.project_id)
        _emit_json(manifest.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "list-tools":
        tools = service.list_tools(config_path=args.config)
        _emit_json([tool.model_dump(mode="json", exclude_none=True) for tool in tools])
        return 0

    if args.command == "extract":
        results = service.extract(
            args.project_root,
            config_path=args.config,
            package_names=args.packages,
        )
        _emit_json([result.model_dump(mode="json", exclude_none=True) for result in results])
        return 0

    if args.command == "decompile-scripts":
        results = service.decompile_scripts(
            args.project_root,
            config_path=args.config,
            input_root=args.input_root,
            output_root=args.output_root,
        )
        _emit_json([result.model_dump(mode="json", exclude_none=True) for result in results])
        return 0

    if args.command == "prepare-krkrdump":
        result = service.prepare_krkrdump(
            args.project_root,
            config_path=args.config,
            output_root=args.output_root,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "preflight":
        result = service.preflight(
            args.project_root,
            config_path=args.config,
            target_stage=PreflightStage(args.stage),
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "build-lines":
        result = service.build_lines(args.project_root, script_root=args.script_root)
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-poc":
        result = service.prepare_poc(
            args.project_root,
            args.voice_root,
            line_id=args.line_id,
            speaker_name=args.speaker,
            contains=args.contains,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-patch":
        result = service.prepare_patch(
            args.project_root,
            args.source_root,
            archive_name=args.archive_name,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "export-dataset":
        result = service.export_dataset(
            args.project_root,
            args.voice_root,
            speaker_name=args.speaker,
            min_lines=args.min_lines,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-gptsovits":
        result = service.prepare_gptsovits(
            args.project_root,
            dataset_root=args.dataset_root,
            speaker_name=args.speaker,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-gptsovits-batch":
        result = service.prepare_gptsovits_batch(
            args.project_root,
            args.speaker,
            limit=args.limit,
            prompt_line_id=args.prompt_line_id,
            reference_mode=args.reference_mode,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-gptsovits-reinject":
        result = service.prepare_gptsovits_reinject(
            args.project_root,
            args.batch_dir,
            target_voice_file=args.target_voice_file,
            source_output_name=args.source_output_name,
            target_sample_rate=args.target_sample_rate,
            archive_name=args.archive_name,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-gptsovits-reinject-batch":
        result = service.prepare_gptsovits_reinject_batch(
            args.project_root,
            args.batch_dir,
            limit=args.limit,
            target_sample_rate=args.target_sample_rate,
            archive_name=args.archive_name,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-gptsovits-train":
        result = service.prepare_gptsovits_training(
            args.project_root,
            args.speaker,
            gpt_sovits_root=args.gpt_sovits_root,
            version=args.version,
            gpu=args.gpu,
            is_half=not args.full_precision,
            gpt_epochs=args.gpt_epochs,
            sovits_epochs=args.sovits_epochs,
            gpt_batch_size=args.gpt_batch_size,
            sovits_batch_size=args.sovits_batch_size,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-gptsovits-production":
        result = service.prepare_gptsovits_production(
            args.project_root,
            speakers=args.speakers,
            min_lines=args.min_lines,
            gpt_sovits_root=args.gpt_sovits_root,
            reference_mode=args.reference_mode,
            inference_limit=args.inference_limit,
            target_sample_rate=args.target_sample_rate,
            api_port=args.api_port,
            sync_game_root=args.sync_game_root,
            gpt_epochs=args.gpt_epochs,
            sovits_epochs=args.sovits_epochs,
            gpt_batch_size=args.gpt_batch_size,
            sovits_batch_size=args.sovits_batch_size,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "run-gptsovits-production":
        result = service.run_gptsovits_production(args.production_root)
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    if args.command == "prepare-final-cleanup":
        result = service.prepare_final_cleanup(
            args.project_root,
            production_name=args.production_name,
            cleanup_name=args.cleanup_name,
        )
        _emit_json(result.model_dump(mode="json", exclude_none=True))
        return 0

    return 1


def _emit_json(payload: object) -> None:
    pretty_json = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(pretty_json)
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))
