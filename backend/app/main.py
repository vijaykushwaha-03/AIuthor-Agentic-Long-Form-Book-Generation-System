"""
AIuthor Backend — FastAPI Application Factory.

Decision DEC-003: create_app() factory pattern for testability.

Usage:
  # Development server (from backend/ directory)
  uvicorn app.main:app --reload

  # Tests use create_app() directly via conftest.py
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_health import router as health_router
from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Run startup tasks before the server begins accepting requests.
    Currently: log a ready message.
    DB ping is attempted but does not block startup (Postgres may not be
    running in test environments that use SQLite overrides).
    """
    settings = get_settings()
    logger.info(
        "AIuthor backend starting. env=%s version=%s",
        settings.APP_ENV,
        settings.APP_VERSION,
    )

    # Attempt DB ping — warn but do not fail if unreachable (e.g., in tests)
    try:
        from app.database import ping_db
        ping_db()
    except Exception as exc:
        logger.warning("DB ping failed on startup (non-fatal in test env): %s", exc)

    yield  # Server is now live and handling requests

    logger.info("AIuthor backend shutting down.")


# ── Application factory ───────────────────────────────────────────────────────
def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Returns a fully configured app instance. Called once at module load
    for the production server; can be called multiple times in tests.
    """
    settings = get_settings()

    app = FastAPI(
        title="AIuthor API",
        description=(
            "Agentic Long-Form Book Generation System. "
            "Generates publication-ready books using a multi-agent LangGraph workflow."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ─────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch any unhandled exception and return a structured JSON error
        instead of an HTML traceback.
        """
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": type(exc).__name__,
                "detail": str(exc),
                "path": str(request.url),
            },
        )

    # ── Routers ──────────────────────────────────────────────────────────────
    app.include_router(health_router)

    return app


# ── Module-level app instance (used by uvicorn) ───────────────────────────────
# `uvicorn app.main:app` picks this up.
app = create_app()
