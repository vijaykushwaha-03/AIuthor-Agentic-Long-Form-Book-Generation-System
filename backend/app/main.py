# """
# AIuthor Backend — FastAPI Application Factory.

# Decision DEC-003: create_app() factory pattern for testability.

# Usage:
#   # Development server (from backend/ directory)
#   uvicorn app.main:app --reload

#   # Tests use create_app() directly via conftest.py
# """
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.api.routes_health import router as health_router
from app.api.routes_books import router as books_router
from app.api.routes_runs import router as runs_router
from app.api.routes_chapters import router as chapters_router
from app.api.routes_sections import router as sections_router
from app.api.routes_rag import router as rag_router
from app.api.routes_memory import router as memory_router
from app.api.routes_observability import router as observability_router
from app.api.routes_eval_export import router as eval_export_router
from app.api.routes_llm import router as llm_router
from app.api.routes_embeddings import router as embeddings_router
from app.api.routes_agents import router as agents_router
from app.api.routes_workflows import router as workflows_router
from app.api.routes_bookrun_workflows import router as bookrun_workflows_router
from app.api.routes_chapter_generation import router as chapter_generation_router
from app.api.routes_chapter_self_healing import router as chapter_self_healing_router
from app.api.routes_memory_extraction import router as memory_extraction_router
from app.api.routes_backend_qa import router as backend_qa_router
from app.api.routes_book_exports import router as book_exports_router
from app.api.routes_delivery_reports import router as delivery_reports_router
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
    app.include_router(books_router)
    app.include_router(delivery_reports_router)
    app.include_router(runs_router)
    app.include_router(chapters_router)
    app.include_router(sections_router)
    app.include_router(rag_router)
    app.include_router(memory_router)
    app.include_router(observability_router)
    app.include_router(book_exports_router)
    app.include_router(eval_export_router)
    app.include_router(llm_router)
    app.include_router(embeddings_router)
    app.include_router(agents_router)
    app.include_router(workflows_router)
    app.include_router(bookrun_workflows_router)
    app.include_router(chapter_generation_router)
    app.include_router(chapter_self_healing_router)
    app.include_router(memory_extraction_router)
    app.include_router(backend_qa_router)

    # ── Static Files & Frontend ──────────────────────────────────────────────
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "AIuthor API - Frontend not found"}




    # ── Admin Dashboard ──────────────────────────────────────────────────────


    from app.admin import setup_admin
    setup_admin(app)

    return app


# ── Module-level app instance (used by uvicorn) ───────────────────────────────
# `uvicorn app.main:app` picks this up.
app = create_app()
