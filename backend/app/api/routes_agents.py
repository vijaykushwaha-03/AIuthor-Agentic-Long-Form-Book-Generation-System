"""
AIuthor Backend — Agent API Routes (Module 7.0B).
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings, Settings
from app.agents import (
    AgentInput,
    AgentOutput,
    AgentInfo,
    AgentPromptRenderRequest,
    AgentPromptRenderResponse,
    AgentNotFoundError,
    AgentPromptError,
    AgentExecutionError,
    AgentError,
)
from app.llm.exceptions import LLMConfigurationError, LLMProviderError
from app.services.agent_execution_service import AgentExecutionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _agent_service(db: DbDep) -> AgentExecutionService:
    return AgentExecutionService(db)


AgentServiceDep = Annotated[AgentExecutionService, Depends(_agent_service)]


def handle_agent_error(exc: Exception) -> None:
    """
    Translates agent and LLM service layer errors to standard FastAPI HTTPExceptions.
    """
    if isinstance(exc, AgentNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "code": "agent_not_found", "details": exc.details},
        )
    elif isinstance(exc, AgentPromptError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "code": "agent_prompt_error", "details": exc.details},
        )
    elif isinstance(exc, AgentExecutionError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": exc.message, "code": "agent_execution_error", "details": exc.details},
        )
    elif isinstance(exc, LLMConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "code": "llm_configuration_error", "details": exc.details},
        )
    elif isinstance(exc, LLMProviderError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": exc.message, "code": "llm_provider_error", "details": exc.details},
        )
    elif isinstance(exc, AgentError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "code": "agent_error", "details": exc.details},
        )
    raise exc


# ══════════════════════════════════════════════════════════════════════════════
# Agent Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "",
    response_model=list[AgentInfo],
    summary="List all supported agents",
    description="Retrieve capability metadata, prompt templates, and versions for all registered agents.",
)
def list_agents(svc: AgentServiceDep) -> list[AgentInfo]:
    try:
        return svc.list_agents()
    except Exception as exc:
        handle_agent_error(exc)


@router.post(
    "/render-prompt",
    response_model=AgentPromptRenderResponse,
    status_code=status.HTTP_200_OK,
    summary="Render prompt template",
    description="Compiles template system and user prompts locally without triggering LLM API generation.",
)
def render_prompt(
    payload: AgentPromptRenderRequest,
    svc: AgentServiceDep,
) -> AgentPromptRenderResponse:
    try:
        return svc.render_agent_prompt(payload)
    except Exception as exc:
        handle_agent_error(exc)


@router.post(
    "/mock-run",
    response_model=AgentOutput,
    status_code=status.HTTP_200_OK,
    summary="Run agent mock execution",
    description="Always forces generation through MockLLMProvider. Safe for offline test coverage.",
)
def mock_run(
    payload: AgentInput,
    svc: AgentServiceDep,
) -> AgentOutput:
    try:
        return svc.run_agent_mock(payload)
    except Exception as exc:
        handle_agent_error(exc)


@router.post(
    "/dev-run-real",
    response_model=AgentOutput,
    status_code=status.HTTP_200_OK,
    summary="Local dev-only real agent execution",
    description=(
        "Local development endpoint to run a single agent execution once against configured "
        "Gemini or OpenAI models. Enabled only when ENABLE_REAL_AGENT_TEST_API=true."
    ),
)
def dev_run_real(
    payload: AgentInput,
    svc: AgentServiceDep,
) -> AgentOutput:
    settings = get_settings()
    if not settings.enable_real_agent_test_api:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Real agent test API is disabled. Set ENABLE_REAL_AGENT_TEST_API=true for local manual testing.",
        )
    try:
        return svc.run_agent_once(payload)
    except Exception as exc:
        handle_agent_error(exc)


@router.get(
    "/{agent_name}",
    response_model=AgentInfo,
    summary="Get single agent info",
    description="Fetch prompt template, enabled status, and parameter requirements for a single agent name.",
)
def get_agent_info(
    agent_name: str,
    svc: AgentServiceDep,
) -> AgentInfo:
    try:
        return svc.get_agent_info(agent_name)
    except Exception as exc:
        handle_agent_error(exc)
