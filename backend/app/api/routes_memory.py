"""
AIuthor Backend — Memory API Routes.

Prefix: None (routes have varying prefixes)
Tags:   memory
"""
from __future__ import annotations

import math
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.error_handlers import handle_service_error
from app.schemas import (
    FactRegistryCreate,
    FactRegistryUpdate,
    FactRegistryResponse,
    ConceptBibleCreate,
    ConceptBibleUpdate,
    ConceptBibleResponse,
    CharacterBibleCreate,
    CharacterBibleUpdate,
    CharacterBibleResponse,
    CallbackIndexCreate,
    CallbackIndexUpdate,
    CallbackIndexResponse,
    ToneFingerprintCreate,
    ToneFingerprintUpdate,
    ToneFingerprintResponse,
    DecisionLogCreate,
    DecisionLogUpdate,
    DecisionLogResponse,
    MemoryReadRequest,
    MemoryReadResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
    PaginatedResponse,
    MessageResponse,
)
from app.services import MemoryService, NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _memory_service(db: DbDep) -> MemoryService:
    return MemoryService(db)


MemoryServiceDep = Annotated[MemoryService, Depends(_memory_service)]


# ══════════════════════════════════════════════════════════════════════════════
# Memory Envelope Endpoints
# NOTE: Declared before detail routes to prevent UUID conflict.
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/read",
    response_model=MemoryReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Read memory envelope",
    description="Retrieve selected groups of memory records for a book.",
)
def read_memory(
    book_id: UUID,
    payload: MemoryReadRequest,
    svc: MemoryServiceDep,
) -> MemoryReadResponse:
    try:
        if payload.book_id != book_id:
            raise ValidationServiceError(
                message=f"Path book_id {book_id} does not match request book_id {payload.book_id}",
                code="book_id_mismatch",
            )
        return svc.read_memory(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/books/{book_id}/memory/write",
    response_model=MemoryWriteResponse,
    status_code=status.HTTP_200_OK,
    summary="Write memory envelope",
    description="Batch write multiple memory groups.",
)
def write_memory(
    book_id: UUID,
    payload: MemoryWriteRequest,
    svc: MemoryServiceDep,
) -> MemoryWriteResponse:
    try:
        if payload.book_id != book_id:
            raise ValidationServiceError(
                message=f"Path book_id {book_id} does not match request book_id {payload.book_id}",
                code="book_id_mismatch",
            )
        return svc.write_memory(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Fact Registry Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/facts",
    response_model=FactRegistryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a fact",
    description="Create a new fact claim scoped to a book project.",
)
def create_fact(
    book_id: UUID,
    payload: FactRegistryCreate,
    svc: MemoryServiceDep,
) -> FactRegistryResponse:
    try:
        fact = svc.create_fact(payload, book_id=book_id)
        return FactRegistryResponse.model_validate(fact)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/facts",
    response_model=PaginatedResponse[FactRegistryResponse],
    summary="List facts",
    description="List facts for a book project.",
)
def list_facts(
    book_id: UUID,
    svc: MemoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str | None = Query(None),
    chapter_id: UUID | None = Query(None),
    search: str | None = Query(None),
) -> PaginatedResponse[FactRegistryResponse]:
    try:
        items, total = svc.list_facts(
            book_id=book_id,
            page=page,
            page_size=page_size,
            status=status,
            chapter_id=chapter_id,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[FactRegistryResponse.model_validate(f) for f in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/facts/{fact_id}",
    response_model=FactRegistryResponse,
    summary="Get fact detail",
)
def get_fact(
    book_id: UUID,
    fact_id: UUID,
    svc: MemoryServiceDep,
) -> FactRegistryResponse:
    try:
        fact = svc.get_fact(book_id, fact_id)
        return FactRegistryResponse.model_validate(fact)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/memory/facts/{fact_id}",
    response_model=FactRegistryResponse,
    summary="Update fact",
)
def update_fact(
    book_id: UUID,
    fact_id: UUID,
    payload: FactRegistryUpdate,
    svc: MemoryServiceDep,
) -> FactRegistryResponse:
    try:
        fact = svc.update_fact(book_id, fact_id, payload)
        return FactRegistryResponse.model_validate(fact)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/memory/facts/{fact_id}",
    response_model=MessageResponse,
    summary="Delete fact",
)
def delete_fact(
    book_id: UUID,
    fact_id: UUID,
    svc: MemoryServiceDep,
) -> MessageResponse:
    try:
        svc.delete_fact(book_id, fact_id)
        return MessageResponse(message=f"Fact {fact_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Concept Bible Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/concepts",
    response_model=ConceptBibleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create concept",
)
def create_concept(
    book_id: UUID,
    payload: ConceptBibleCreate,
    svc: MemoryServiceDep,
) -> ConceptBibleResponse:
    try:
        concept = svc.create_concept(payload, book_id=book_id)
        return ConceptBibleResponse.model_validate(concept)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/concepts",
    response_model=PaginatedResponse[ConceptBibleResponse],
    summary="List concepts",
)
def list_concepts(
    book_id: UUID,
    svc: MemoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
) -> PaginatedResponse[ConceptBibleResponse]:
    try:
        items, total = svc.list_concepts(
            book_id=book_id,
            page=page,
            page_size=page_size,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[ConceptBibleResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/concepts/{concept_id}",
    response_model=ConceptBibleResponse,
    summary="Get concept detail",
)
def get_concept(
    book_id: UUID,
    concept_id: UUID,
    svc: MemoryServiceDep,
) -> ConceptBibleResponse:
    try:
        concept = svc.get_concept(book_id, concept_id)
        return ConceptBibleResponse.model_validate(concept)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/memory/concepts/{concept_id}",
    response_model=ConceptBibleResponse,
    summary="Update concept",
)
def update_concept(
    book_id: UUID,
    concept_id: UUID,
    payload: ConceptBibleUpdate,
    svc: MemoryServiceDep,
) -> ConceptBibleResponse:
    try:
        concept = svc.update_concept(book_id, concept_id, payload)
        return ConceptBibleResponse.model_validate(concept)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/memory/concepts/{concept_id}",
    response_model=MessageResponse,
    summary="Delete concept",
)
def delete_concept(
    book_id: UUID,
    concept_id: UUID,
    svc: MemoryServiceDep,
) -> MessageResponse:
    try:
        svc.delete_concept(book_id, concept_id)
        return MessageResponse(message=f"Concept {concept_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Character Bible Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/characters",
    response_model=CharacterBibleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create character",
)
def create_character(
    book_id: UUID,
    payload: CharacterBibleCreate,
    svc: MemoryServiceDep,
) -> CharacterBibleResponse:
    try:
        char = svc.create_character(payload, book_id=book_id)
        return CharacterBibleResponse.model_validate(char)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/characters",
    response_model=PaginatedResponse[CharacterBibleResponse],
    summary="List characters",
)
def list_characters(
    book_id: UUID,
    svc: MemoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
) -> PaginatedResponse[CharacterBibleResponse]:
    try:
        items, total = svc.list_characters(
            book_id=book_id,
            page=page,
            page_size=page_size,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[CharacterBibleResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/characters/{character_id}",
    response_model=CharacterBibleResponse,
    summary="Get character detail",
)
def get_character(
    book_id: UUID,
    character_id: UUID,
    svc: MemoryServiceDep,
) -> CharacterBibleResponse:
    try:
        char = svc.get_character(book_id, character_id)
        return CharacterBibleResponse.model_validate(char)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/memory/characters/{character_id}",
    response_model=CharacterBibleResponse,
    summary="Update character",
)
def update_character(
    book_id: UUID,
    character_id: UUID,
    payload: CharacterBibleUpdate,
    svc: MemoryServiceDep,
) -> CharacterBibleResponse:
    try:
        char = svc.update_character(book_id, character_id, payload)
        return CharacterBibleResponse.model_validate(char)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/memory/characters/{character_id}",
    response_model=MessageResponse,
    summary="Delete character",
)
def delete_character(
    book_id: UUID,
    character_id: UUID,
    svc: MemoryServiceDep,
) -> MessageResponse:
    try:
        svc.delete_character(book_id, character_id)
        return MessageResponse(message=f"Character {character_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Callback Index Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/callbacks",
    response_model=CallbackIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create callback",
)
def create_callback(
    book_id: UUID,
    payload: CallbackIndexCreate,
    svc: MemoryServiceDep,
) -> CallbackIndexResponse:
    try:
        cb = svc.create_callback(payload, book_id=book_id)
        return CallbackIndexResponse.model_validate(cb)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/callbacks",
    response_model=PaginatedResponse[CallbackIndexResponse],
    summary="List callbacks",
)
def list_callbacks(
    book_id: UUID,
    svc: MemoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str | None = Query(None),
    source_chapter: int | None = Query(None),
    target_chapter: int | None = Query(None),
    search: str | None = Query(None),
) -> PaginatedResponse[CallbackIndexResponse]:
    try:
        items, total = svc.list_callbacks(
            book_id=book_id,
            page=page,
            page_size=page_size,
            status=status,
            source_chapter=source_chapter,
            target_chapter=target_chapter,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[CallbackIndexResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/callbacks/{callback_id}",
    response_model=CallbackIndexResponse,
    summary="Get callback detail",
)
def get_callback(
    book_id: UUID,
    callback_id: UUID,
    svc: MemoryServiceDep,
) -> CallbackIndexResponse:
    try:
        cb = svc.get_callback(book_id, callback_id)
        return CallbackIndexResponse.model_validate(cb)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/memory/callbacks/{callback_id}",
    response_model=CallbackIndexResponse,
    summary="Update callback",
)
def update_callback(
    book_id: UUID,
    callback_id: UUID,
    payload: CallbackIndexUpdate,
    svc: MemoryServiceDep,
) -> CallbackIndexResponse:
    try:
        cb = svc.update_callback(book_id, callback_id, payload)
        return CallbackIndexResponse.model_validate(cb)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/memory/callbacks/{callback_id}",
    response_model=MessageResponse,
    summary="Delete callback",
)
def delete_callback(
    book_id: UUID,
    callback_id: UUID,
    svc: MemoryServiceDep,
) -> MessageResponse:
    try:
        svc.delete_callback(book_id, callback_id)
        return MessageResponse(message=f"Callback {callback_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Tone Fingerprint Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/tone-fingerprints",
    response_model=ToneFingerprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tone fingerprint",
)
def create_tone_fingerprint(
    book_id: UUID,
    payload: ToneFingerprintCreate,
    svc: MemoryServiceDep,
) -> ToneFingerprintResponse:
    try:
        tone = svc.create_tone_fingerprint(payload, book_id=book_id)
        return ToneFingerprintResponse.model_validate(tone)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/tone-fingerprints",
    response_model=PaginatedResponse[ToneFingerprintResponse],
    summary="List tone fingerprints",
)
def list_tone_fingerprints(
    book_id: UUID,
    svc: MemoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tone_name: str | None = Query(None),
) -> PaginatedResponse[ToneFingerprintResponse]:
    try:
        items, total = svc.list_tone_fingerprints(
            book_id=book_id,
            page=page,
            page_size=page_size,
            tone_name=tone_name,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[ToneFingerprintResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/tone-fingerprints/{tone_id}",
    response_model=ToneFingerprintResponse,
    summary="Get tone fingerprint detail",
)
def get_tone_fingerprint(
    book_id: UUID,
    tone_id: UUID,
    svc: MemoryServiceDep,
) -> ToneFingerprintResponse:
    try:
        tone = svc.get_tone_fingerprint(book_id, tone_id)
        return ToneFingerprintResponse.model_validate(tone)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/memory/tone-fingerprints/{tone_id}",
    response_model=ToneFingerprintResponse,
    summary="Update tone fingerprint",
)
def update_tone_fingerprint(
    book_id: UUID,
    tone_id: UUID,
    payload: ToneFingerprintUpdate,
    svc: MemoryServiceDep,
) -> ToneFingerprintResponse:
    try:
        tone = svc.update_tone_fingerprint(book_id, tone_id, payload)
        return ToneFingerprintResponse.model_validate(tone)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/memory/tone-fingerprints/{tone_id}",
    response_model=MessageResponse,
    summary="Delete tone fingerprint",
)
def delete_tone_fingerprint(
    book_id: UUID,
    tone_id: UUID,
    svc: MemoryServiceDep,
) -> MessageResponse:
    try:
        svc.delete_tone_fingerprint(book_id, tone_id)
        return MessageResponse(message=f"Tone fingerprint {tone_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Decision Log Endpoints — Book-scoped
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/memory/decisions",
    response_model=DecisionLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create decision",
)
def create_decision(
    book_id: UUID,
    payload: DecisionLogCreate,
    svc: MemoryServiceDep,
) -> DecisionLogResponse:
    try:
        decision = svc.create_decision(payload, book_id=book_id)
        return DecisionLogResponse.model_validate(decision)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/decisions",
    response_model=PaginatedResponse[DecisionLogResponse],
    summary="List decisions for a book",
)
def list_book_decisions(
    book_id: UUID,
    svc: MemoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
) -> PaginatedResponse[DecisionLogResponse]:
    try:
        items, total = svc.list_decisions(
            book_id=book_id,
            page=page,
            page_size=page_size,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[DecisionLogResponse.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/memory/decisions/{decision_id}",
    response_model=DecisionLogResponse,
    summary="Get decision detail",
)
def get_book_decision(
    book_id: UUID,
    decision_id: UUID,
    svc: MemoryServiceDep,
) -> DecisionLogResponse:
    try:
        decision = svc.get_decision(decision_id)
        if decision.book_id != book_id:
            raise NotFoundError(
                message="Decision log entry not found in this book",
                code="decision_log_not_found",
                details={"decision_id": str(decision_id), "book_id": str(book_id)},
            )
        return DecisionLogResponse.model_validate(decision)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/memory/decisions/{decision_id}",
    response_model=DecisionLogResponse,
    summary="Update decision",
)
def update_book_decision(
    book_id: UUID,
    decision_id: UUID,
    payload: DecisionLogUpdate,
    svc: MemoryServiceDep,
) -> DecisionLogResponse:
    try:
        # Verify book-scoped access first
        decision = svc.get_decision(decision_id)
        if decision.book_id != book_id:
            raise NotFoundError(
                message="Decision log entry not found in this book",
                code="decision_log_not_found",
                details={"decision_id": str(decision_id), "book_id": str(book_id)},
            )
        updated = svc.update_decision(decision_id, payload)
        return DecisionLogResponse.model_validate(updated)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/memory/decisions/{decision_id}",
    response_model=MessageResponse,
    summary="Delete decision",
)
def delete_book_decision(
    book_id: UUID,
    decision_id: UUID,
    svc: MemoryServiceDep,
) -> MessageResponse:
    try:
        # Verify book-scoped access first
        decision = svc.get_decision(decision_id)
        if decision.book_id != book_id:
            raise NotFoundError(
                message="Decision log entry not found in this book",
                code="decision_log_not_found",
                details={"decision_id": str(decision_id), "book_id": str(book_id)},
            )
        svc.delete_decision(decision_id)
        return MessageResponse(message=f"Decision log {decision_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Decision Log Endpoints — Global
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/api/memory/decisions",
    response_model=PaginatedResponse[DecisionLogResponse],
    summary="List decisions globally",
)
def list_global_decisions(
    svc: MemoryServiceDep,
    book_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
) -> PaginatedResponse[DecisionLogResponse]:
    try:
        items, total = svc.list_decisions(
            book_id=book_id,
            page=page,
            page_size=page_size,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[DecisionLogResponse.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
