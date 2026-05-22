"""
AIuthor Backend — Health & Version Endpoints.

Decision DEC-005:
  GET /health  → root level (load-balancer / k8s liveness probe)
  GET /api/version → under /api/ prefix (API metadata for consumers)
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(tags=["health"])


# ── Response schemas ──────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    env: str
    version: str


class VersionResponse(BaseModel):
    version: str
    service: str


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Lightweight liveness probe. Returns 200 when the service is running. "
        "Used by load balancers and container orchestrators."
    ),
)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        env=settings.APP_ENV,
        version=settings.APP_VERSION,
    )


@router.get(
    "/api/version",
    response_model=VersionResponse,
    summary="API version",
    description="Returns the current API version and service name.",
)
def api_version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(
        version=settings.APP_VERSION,
        service="aiuthor-backend",
    )
