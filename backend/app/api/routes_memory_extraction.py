"""
AIuthor Backend — Memory Extraction API Routes (Module 9.0).
"""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.error_handlers import handle_service_error
from app.config import get_settings
from app.workflows.schemas import (
    MemoryExtractionRequest,
    MemoryExtractionResponse,
    ContinuityPackRequest,
    ContinuityPackResponse,
)
from app.services import (
    MemoryExtractionService,
    ContinuityPackService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory-extraction"])

# ── Dependencies ─────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _memory_extraction_service(db: DbDep) -> MemoryExtractionService:
    return MemoryExtractionService(db)


def _continuity_pack_service(db: DbDep) -> ContinuityPackService:
    return ContinuityPackService(db)


MemoryExtractionServiceDep = Annotated[
    MemoryExtractionService, Depends(_memory_extraction_service)
]
ContinuityPackServiceDep = Annotated[
    ContinuityPackService, Depends(_continuity_pack_service)
]



# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/api/books/{book_id}/memory/extract/dev-run-real",
    response_model=MemoryExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract memory candidates (Real Dev Run)",
    description="Run real Gemini/OpenAI MemoryKeeper agent execution for extraction, gated for local dev testing.",
)
def extract_memory_real(
    book_id: UUID,
    payload: MemoryExtractionRequest,
    svc: MemoryExtractionServiceDep,
) -> MemoryExtractionResponse:

    try:
        # Force book_id and real execution mode
        payload_copy = payload.model_copy(
            update={"book_id": book_id, "execution_mode": "real_dev"}
        )
        return svc.extract_memory(payload_copy)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)



@router.post(
    "/api/books/{book_id}/memory/extract/from-chapter/{chapter_id}/dev-run-real",
    response_model=MemoryExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract memory from chapter (Real Dev Run)",
    description="Extract memory from chapter draft/final text using the real MemoryKeeper agent, gated for local dev testing.",
)
def extract_chapter_memory_real(
    book_id: UUID,
    chapter_id: UUID,
    payload: MemoryExtractionRequest,
    svc: MemoryExtractionServiceDep,
) -> MemoryExtractionResponse:

    try:
        # Force book_id, chapter_id, source_type=chapter, execution_mode=real_dev
        payload_copy = payload.model_copy(
            update={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "source_type": "chapter",
                "execution_mode": "real_dev",
            }
        )
        return svc.extract_memory(payload_copy)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/books/{book_id}/memory/continuity-pack",
    response_model=ContinuityPackResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Continuity Pack",
    description="Compile stored memory records for a book into a unified continuity text document without invoking LLMs.",
)
def build_continuity_pack(
    book_id: UUID,
    payload: ContinuityPackRequest,
    svc: ContinuityPackServiceDep,
) -> ContinuityPackResponse:
    try:
        # Force book_id matches path parameter
        payload_copy = payload.model_copy(update={"book_id": book_id})
        return svc.build_continuity_pack(payload_copy)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
