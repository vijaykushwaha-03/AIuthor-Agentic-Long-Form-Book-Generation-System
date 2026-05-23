"""
AIuthor Backend — Observability API Routes.

Prefix: None (routes have varying prefixes)
Tags:   observability
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
    AgentTraceCreate,
    AgentTraceUpdate,
    AgentTraceResponse,
    PromptLogCreate,
    PromptLogUpdate,
    PromptLogResponse,
    MemoryIOLogCreate,
    MemoryIOLogResponse,
    TokenCostLedgerCreate,
    TokenCostLedgerUpdate,
    TokenCostLedgerResponse,
    TraceBundleResponse,
    RunCostSummaryResponse,
    PaginatedResponse,
    MessageResponse,
)
from app.services import ObservabilityService, NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _observability_service(db: DbDep) -> ObservabilityService:
    return ObservabilityService(db)


ObservabilityServiceDep = Annotated[ObservabilityService, Depends(_observability_service)]


# ══════════════════════════════════════════════════════════════════════════════
# Agent Trace Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/runs/{run_id}/observability/traces",
    response_model=AgentTraceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent trace",
    description="Log a new execution trace for an agent call in a run. Path run_id is the source of truth.",
)
def create_agent_trace(
    run_id: UUID,
    payload: AgentTraceCreate,
    svc: ObservabilityServiceDep,
) -> AgentTraceResponse:
    try:
        trace = svc.create_agent_trace(payload, run_id=run_id)
        return AgentTraceResponse.model_validate(trace)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/observability/traces",
    response_model=PaginatedResponse[AgentTraceResponse],
    summary="List agent traces for a run",
)
def list_agent_traces(
    run_id: UUID,
    svc: ObservabilityServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    agent_name: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
) -> PaginatedResponse[AgentTraceResponse]:
    try:
        items, total = svc.list_agent_traces(
            run_id=run_id,
            page=page,
            page_size=page_size,
            agent_name=agent_name,
            status=status_filter,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[AgentTraceResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/observability/traces/{trace_id}",
    response_model=AgentTraceResponse,
    summary="Get agent trace detail",
)
def get_agent_trace(
    trace_id: UUID,
    svc: ObservabilityServiceDep,
) -> AgentTraceResponse:
    try:
        trace = svc.get_agent_trace(trace_id)
        return AgentTraceResponse.model_validate(trace)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/observability/traces/{trace_id}",
    response_model=AgentTraceResponse,
    summary="Update agent trace",
)
def update_agent_trace(
    trace_id: UUID,
    payload: AgentTraceUpdate,
    svc: ObservabilityServiceDep,
) -> AgentTraceResponse:
    try:
        trace = svc.update_agent_trace(trace_id, payload)
        return AgentTraceResponse.model_validate(trace)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/observability/traces/{trace_id}",
    response_model=MessageResponse,
    summary="Delete agent trace",
)
def delete_agent_trace(
    trace_id: UUID,
    svc: ObservabilityServiceDep,
) -> MessageResponse:
    try:
        svc.delete_agent_trace(trace_id)
        return MessageResponse(message=f"Agent trace {trace_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Prompt Log Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/runs/{run_id}/observability/prompts",
    response_model=PromptLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create prompt log",
    description="Log a complete prompt and payload context for a run. Path run_id is the source of truth.",
)
def create_prompt_log(
    run_id: UUID,
    payload: PromptLogCreate,
    svc: ObservabilityServiceDep,
) -> PromptLogResponse:
    try:
        log = svc.create_prompt_log(payload, run_id=run_id)
        return PromptLogResponse.model_validate(log)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/observability/prompts",
    response_model=PaginatedResponse[PromptLogResponse],
    summary="List prompt logs for a run",
)
def list_prompt_logs(
    run_id: UUID,
    svc: ObservabilityServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    agent_name: str | None = Query(None),
    model_name: str | None = Query(None),
    prompt_name: str | None = Query(None),
    search: str | None = Query(None),
) -> PaginatedResponse[PromptLogResponse]:
    try:
        items, total = svc.list_prompt_logs(
            run_id=run_id,
            page=page,
            page_size=page_size,
            agent_name=agent_name,
            model_name=model_name,
            prompt_name=prompt_name,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[PromptLogResponse.model_validate(l) for l in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/observability/prompts/{prompt_log_id}",
    response_model=PromptLogResponse,
    summary="Get prompt log detail",
)
def get_prompt_log(
    prompt_log_id: UUID,
    svc: ObservabilityServiceDep,
) -> PromptLogResponse:
    try:
        log = svc.get_prompt_log(prompt_log_id)
        return PromptLogResponse.model_validate(log)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/observability/prompts/{prompt_log_id}",
    response_model=PromptLogResponse,
    summary="Update prompt log",
)
def update_prompt_log(
    prompt_log_id: UUID,
    payload: PromptLogUpdate,
    svc: ObservabilityServiceDep,
) -> PromptLogResponse:
    try:
        log = svc.update_prompt_log(prompt_log_id, payload)
        return PromptLogResponse.model_validate(log)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/observability/prompts/{prompt_log_id}",
    response_model=MessageResponse,
    summary="Delete prompt log",
)
def delete_prompt_log(
    prompt_log_id: UUID,
    svc: ObservabilityServiceDep,
) -> MessageResponse:
    try:
        svc.delete_prompt_log(prompt_log_id)
        return MessageResponse(message=f"Prompt log {prompt_log_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Memory I/O Log Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/runs/{run_id}/observability/memory-io",
    response_model=MemoryIOLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create memory IO log",
    description="Log a memory read or write operation during run execution. Path run_id is the source of truth.",
)
def create_memory_io_log(
    run_id: UUID,
    payload: MemoryIOLogCreate,
    svc: ObservabilityServiceDep,
) -> MemoryIOLogResponse:
    try:
        log = svc.create_memory_io_log(payload, run_id=run_id)
        return MemoryIOLogResponse.model_validate(log)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/observability/memory-io",
    response_model=PaginatedResponse[MemoryIOLogResponse],
    summary="List memory IO logs for a run",
)
def list_memory_io_logs(
    run_id: UUID,
    svc: ObservabilityServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    agent_name: str | None = Query(None),
    operation: str | None = Query(None),
    memory_type: str | None = Query(None),
) -> PaginatedResponse[MemoryIOLogResponse]:
    try:
        items, total = svc.list_memory_io_logs(
            run_id=run_id,
            page=page,
            page_size=page_size,
            agent_name=agent_name,
            operation=operation,
            memory_type=memory_type,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[MemoryIOLogResponse.model_validate(l) for l in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/observability/memory-io/{log_id}",
    response_model=MemoryIOLogResponse,
    summary="Get memory IO log detail",
)
def get_memory_io_log(
    log_id: UUID,
    svc: ObservabilityServiceDep,
) -> MemoryIOLogResponse:
    try:
        log = svc.get_memory_io_log(log_id)
        return MemoryIOLogResponse.model_validate(log)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/observability/memory-io/{log_id}",
    response_model=MessageResponse,
    summary="Delete memory IO log",
)
def delete_memory_io_log(
    log_id: UUID,
    svc: ObservabilityServiceDep,
) -> MessageResponse:
    try:
        svc.delete_memory_io_log(log_id)
        return MessageResponse(message=f"Memory IO log {log_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Token Cost Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/runs/{run_id}/observability/token-costs",
    response_model=TokenCostLedgerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create token cost ledger record",
    description="Log token usage and cost per model call. Path run_id is the source of truth.",
)
def create_token_cost(
    run_id: UUID,
    payload: TokenCostLedgerCreate,
    svc: ObservabilityServiceDep,
) -> TokenCostLedgerResponse:
    try:
        cost = svc.create_token_cost(payload, run_id=run_id)
        return TokenCostLedgerResponse.model_validate(cost)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/observability/token-costs",
    response_model=PaginatedResponse[TokenCostLedgerResponse],
    summary="List token cost ledger entries for a run",
)
def list_token_costs(
    run_id: UUID,
    svc: ObservabilityServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    agent_name: str | None = Query(None),
    model_name: str | None = Query(None),
) -> PaginatedResponse[TokenCostLedgerResponse]:
    try:
        items, total = svc.list_token_costs(
            run_id=run_id,
            page=page,
            page_size=page_size,
            agent_name=agent_name,
            model_name=model_name,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[TokenCostLedgerResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/observability/token-costs/{cost_id}",
    response_model=TokenCostLedgerResponse,
    summary="Get token cost detail",
)
def get_token_cost(
    cost_id: UUID,
    svc: ObservabilityServiceDep,
) -> TokenCostLedgerResponse:
    try:
        cost = svc.get_token_cost(cost_id)
        return TokenCostLedgerResponse.model_validate(cost)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/observability/token-costs/{cost_id}",
    response_model=TokenCostLedgerResponse,
    summary="Update token cost",
)
def update_token_cost(
    cost_id: UUID,
    payload: TokenCostLedgerUpdate,
    svc: ObservabilityServiceDep,
) -> TokenCostLedgerResponse:
    try:
        cost = svc.update_token_cost(cost_id, payload)
        return TokenCostLedgerResponse.model_validate(cost)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/observability/token-costs/{cost_id}",
    response_model=MessageResponse,
    summary="Delete token cost",
)
def delete_token_cost(
    cost_id: UUID,
    svc: ObservabilityServiceDep,
) -> MessageResponse:
    try:
        svc.delete_token_cost(cost_id)
        return MessageResponse(message=f"Token cost ledger entry {cost_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Trace Bundle & Cost Summary Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/api/runs/{run_id}/observability/trace-bundle",
    response_model=TraceBundleResponse,
    summary="Get run trace bundle",
    description="Compile and return all trace, prompt log, memory IO, and token ledger rows for a run execution.",
)
def get_trace_bundle(
    run_id: UUID,
    svc: ObservabilityServiceDep,
) -> TraceBundleResponse:
    try:
        return svc.get_trace_bundle(run_id)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/observability/cost-summary",
    response_model=RunCostSummaryResponse,
    summary="Get run cost summary",
    description="Compile aggregate token counts and estimated cost grouped by model breakdown for a run.",
)
def get_run_cost_summary(
    run_id: UUID,
    svc: ObservabilityServiceDep,
) -> RunCostSummaryResponse:
    try:
        return svc.get_run_cost_summary(run_id)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
