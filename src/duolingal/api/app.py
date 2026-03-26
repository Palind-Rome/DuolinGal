from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are missing.
    FastAPI = None
    HTTPException = RuntimeError

from duolingal.domain.models import (
    AnalyzeRequest,
    BuildLinesRequest,
    DecompileScriptsRequest,
    ExtractionResult,
    ExtractRequest,
    GameAnalysis,
    InitProjectRequest,
    LinesBuildResult,
    PreflightReport,
    PreflightRequest,
    ProjectManifest,
    ScriptDecompileResult,
    ToolRequirement,
)
from duolingal.services.project_service import ProjectService


def create_app() -> FastAPI:
    if FastAPI is None:
        raise RuntimeError("FastAPI 未安装。请先执行 `pip install -e .[api]`。")

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

    return app
