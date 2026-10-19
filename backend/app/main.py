from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, blockchain, cases, dummy, health, me, receipts, rules
from app.core.config import get_settings
from app.services.analysis import AnalysisError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @app.exception_handler(AnalysisError)
    async def analysis_failed(request: Request, exc: AnalysisError) -> JSONResponse:
        # for example: the legal dataset failed its integrity check
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    for module in (health, me, receipts, cases, dummy, rules, admin, blockchain):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
