from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are missing.
    FastAPI = None
    HTTPException = RuntimeError

from duolingal.domain.models import AnalyzeRequest, GameAnalysis, InitProjectRequest, ProjectManifest, ToolRequirement
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
    def list_tools() -> list[ToolRequirement]:
        return service.list_tools()

    @app.post("/api/analyze", response_model=GameAnalysis)
    def analyze(request: AnalyzeRequest) -> GameAnalysis:
        return service.analyze(request.game_path)

    @app.post("/api/projects/init", response_model=ProjectManifest)
    def init_project(request: InitProjectRequest) -> ProjectManifest:
        try:
            return service.init_project(request.game_path, project_id=request.project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
