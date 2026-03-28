from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are missing.
    FastAPI = None
    HTTPException = RuntimeError

from duolingal.domain.models import (
    AnalyzeRequest,
    BuildLinesRequest,
    DatasetExportResult,
    DecompileScriptsRequest,
    ExportDatasetRequest,
    ExtractionResult,
    ExtractRequest,
    GameAnalysis,
    GptSovitsBatchResult,
    GptSovitsPreparationResult,
    GptSovitsReinjectResult,
    GptSovitsTrainingPreparationResult,
    InitProjectRequest,
    KrkrDumpPreparationResult,
    LinesBuildResult,
    PatchPreparationResult,
    PocPreparationResult,
    PreflightReport,
    PreflightRequest,
    PrepareGptSovitsRequest,
    PrepareGptSovitsBatchRequest,
    PrepareGptSovitsReinjectRequest,
    PrepareGptSovitsTrainingRequest,
    PrepareKrkrDumpRequest,
    PreparePatchRequest,
    PreparePocRequest,
    ProjectManifest,
    ScriptDecompileResult,
    ToolRequirement,
)
from duolingal.services.project_service import ProjectService


def create_app() -> FastAPI:
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Run `pip install -e .[api]` first.")

    service = ProjectService()
    app = FastAPI(
        title="DuolinGal API",
        version="0.1.0",
        summary="Local-first API for galgame analysis and pipeline bootstrap.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tools", response_model=list[ToolRequirement])
    def list_tools(config_path: str | None = None) -> list[ToolRequirement]:
        return service.list_tools(config_path=config_path)

    @app.post("/api/analyze", response_model=GameAnalysis)
    def analyze(request: AnalyzeRequest) -> GameAnalysis:
        return service.analyze(request.game_path)

    @app.post("/api/projects/init", response_model=ProjectManifest)
    def init_project(request: InitProjectRequest) -> ProjectManifest:
        try:
            return service.init_project(request.game_path, project_id=request.project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/extract", response_model=list[ExtractionResult])
    def extract_project(request: ExtractRequest) -> list[ExtractionResult]:
        try:
            return service.extract(
                request.project_root,
                config_path=request.config_path,
                package_names=request.package_names,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/decompile-scripts", response_model=list[ScriptDecompileResult])
    def decompile_scripts(request: DecompileScriptsRequest) -> list[ScriptDecompileResult]:
        try:
            return service.decompile_scripts(
                request.project_root,
                config_path=request.config_path,
                input_root=request.input_root,
                output_root=request.output_root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-krkrdump", response_model=KrkrDumpPreparationResult)
    def prepare_krkrdump(request: PrepareKrkrDumpRequest) -> KrkrDumpPreparationResult:
        try:
            return service.prepare_krkrdump(
                request.project_root,
                config_path=request.config_path,
                output_root=request.output_root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/preflight", response_model=PreflightReport)
    def preflight(request: PreflightRequest) -> PreflightReport:
        try:
            return service.preflight(
                request.project_root,
                config_path=request.config_path,
                target_stage=request.target_stage,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/build-lines", response_model=LinesBuildResult)
    def build_lines(request: BuildLinesRequest) -> LinesBuildResult:
        try:
            return service.build_lines(request.project_root, script_root=request.script_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-poc", response_model=PocPreparationResult)
    def prepare_poc(request: PreparePocRequest) -> PocPreparationResult:
        try:
            return service.prepare_poc(
                request.project_root,
                request.voice_root,
                line_id=request.line_id,
                speaker_name=request.speaker_name,
                contains=request.contains,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-patch", response_model=PatchPreparationResult)
    def prepare_patch(request: PreparePatchRequest) -> PatchPreparationResult:
        try:
            return service.prepare_patch(
                request.project_root,
                request.source_root,
                archive_name=request.archive_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/export-dataset", response_model=DatasetExportResult)
    def export_dataset(request: ExportDatasetRequest) -> DatasetExportResult:
        try:
            return service.export_dataset(
                request.project_root,
                request.voice_root,
                speaker_name=request.speaker_name,
                min_lines=request.min_lines,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-gptsovits", response_model=GptSovitsPreparationResult)
    def prepare_gptsovits(request: PrepareGptSovitsRequest) -> GptSovitsPreparationResult:
        try:
            return service.prepare_gptsovits(
                request.project_root,
                dataset_root=request.dataset_root,
                speaker_name=request.speaker_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-gptsovits-batch", response_model=GptSovitsBatchResult)
    def prepare_gptsovits_batch(request: PrepareGptSovitsBatchRequest) -> GptSovitsBatchResult:
        try:
            return service.prepare_gptsovits_batch(
                request.project_root,
                request.speaker_name,
                limit=request.limit,
                prompt_line_id=request.prompt_line_id,
                reference_mode=request.reference_mode,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-gptsovits-reinject", response_model=GptSovitsReinjectResult)
    def prepare_gptsovits_reinject(request: PrepareGptSovitsReinjectRequest) -> GptSovitsReinjectResult:
        try:
            return service.prepare_gptsovits_reinject(
                request.project_root,
                request.batch_dir,
                target_voice_file=request.target_voice_file,
                source_output_name=request.source_output_name,
                target_sample_rate=request.target_sample_rate,
                archive_name=request.archive_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/prepare-gptsovits-train", response_model=GptSovitsTrainingPreparationResult)
    def prepare_gptsovits_train(request: PrepareGptSovitsTrainingRequest) -> GptSovitsTrainingPreparationResult:
        try:
            return service.prepare_gptsovits_training(
                request.project_root,
                request.speaker_name,
                gpt_sovits_root=request.gpt_sovits_root,
                version=request.version,
                gpu=request.gpu,
                is_half=request.is_half,
                gpt_epochs=request.gpt_epochs,
                sovits_epochs=request.sovits_epochs,
                gpt_batch_size=request.gpt_batch_size,
                sovits_batch_size=request.sovits_batch_size,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
