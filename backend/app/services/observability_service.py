"""
AIuthor Backend — Observability Service.

Encapsulates all database operations for observability resources: AgentTrace,
PromptLog, MemoryIOLog, TokenCostLedger, and execution run trace bundles.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models import (
    BookProject,
    BookRun,
    AgentTrace,
    PromptLog,
    MemoryIOLog,
    TokenCostLedger,
)
from app.schemas import (
    AgentTraceCreate,
    AgentTraceUpdate,
    PromptLogCreate,
    PromptLogUpdate,
    MemoryIOLogCreate,
    TokenCostLedgerCreate,
    TokenCostLedgerUpdate,
    TraceBundleResponse,
    RunCostSummaryResponse,
)
from app.services.exceptions import NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)


class ObservabilityService:
    """
    Service layer for observability operations.

    All write operations commit + refresh; any DB error causes a rollback before re-raising.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit(self) -> None:
        """Commit the current transaction; rollback and re-raise on failure."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _verify_run(self, run_id: UUID) -> BookRun:
        """Confirm BookRun exists, else raise NotFoundError."""
        run = self.db.get(BookRun, run_id)
        if run is None:
            raise NotFoundError(
                message="Book run not found",
                code="run_not_found",
                details={"run_id": str(run_id)},
            )
        return run

    def _verify_book_optional(self, book_id: UUID | None) -> BookProject | None:
        """Confirm BookProject exists if book_id is provided, else raise NotFoundError."""
        if book_id is None:
            return None
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _enum_to_str(self, value: Any) -> str | None:
        """Convert enum values to string where needed."""
        if value is None:
            return None
        if hasattr(value, "value"):
            return value.value
        return str(value)

    def _paginate(self, query: Any, page: int, page_size: int) -> tuple[list[Any], int]:
        """Apply page and page_size pagination filters and return items and total count."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    # ── Agent Trace methods ────────────────────────────────────────────────────

    def create_agent_trace(self, payload: AgentTraceCreate, run_id: UUID | None = None) -> AgentTrace:
        """Create a new agent trace log."""
        effective_run_id = run_id if run_id is not None else payload.run_id
        self._verify_run(effective_run_id)
        self._verify_book_optional(payload.book_id)

        trace = AgentTrace(
            run_id=effective_run_id,
            book_id=payload.book_id,
            agent_name=self._enum_to_str(payload.agent_name),
            input_summary=payload.input_summary,
            output_summary=payload.output_summary,
            status=self._enum_to_str(payload.status),
            error_message=payload.error_message,
            started_at=payload.started_at,
            completed_at=payload.completed_at,
            trace_metadata=payload.trace_metadata,
        )
        self.db.add(trace)
        self._commit()
        self.db.refresh(trace)
        logger.info("Created AgentTrace id=%s for run_id=%s", trace.id, effective_run_id)
        return trace

    def get_agent_trace(self, trace_id: UUID) -> AgentTrace:
        """Fetch an agent trace by id."""
        trace = self.db.get(AgentTrace, trace_id)
        if trace is None:
            raise NotFoundError(
                message="Agent trace not found",
                code="trace_not_found",
                details={"trace_id": str(trace_id)},
            )
        return trace

    def get_agent_trace_for_run(self, run_id: UUID, trace_id: UUID) -> AgentTrace:
        """Fetch an agent trace scoped to a run."""
        self._verify_run(run_id)
        trace = (
            self.db.query(AgentTrace)
            .filter(AgentTrace.id == trace_id, AgentTrace.run_id == run_id)
            .first()
        )
        if trace is None:
            raise NotFoundError(
                message="Agent trace not found in this run",
                code="trace_not_found",
                details={"trace_id": str(trace_id), "run_id": str(run_id)},
            )
        return trace

    def list_agent_traces(
        self,
        run_id: UUID | None = None,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AgentTrace], int]:
        """List paginated agent traces sorted ascending by created_at."""
        query = self.db.query(AgentTrace)
        if run_id is not None:
            query = query.filter(AgentTrace.run_id == run_id)
        if book_id is not None:
            query = query.filter(AgentTrace.book_id == book_id)
        if agent_name is not None:
            query = query.filter(AgentTrace.agent_name == self._enum_to_str(agent_name))
        if status is not None:
            query = query.filter(AgentTrace.status == self._enum_to_str(status))

        query = query.order_by(asc(AgentTrace.created_at))
        return self._paginate(query, page, page_size)

    def update_agent_trace(self, trace_id: UUID, payload: AgentTraceUpdate, run_id: UUID | None = None) -> AgentTrace:
        """Apply a partial update to an agent trace."""
        if run_id is not None:
            trace = self.get_agent_trace_for_run(run_id, trace_id)
        else:
            trace = self.get_agent_trace(trace_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status":
                value = self._enum_to_str(value)
            setattr(trace, field, value)

        self._commit()
        self.db.refresh(trace)
        logger.info("Updated AgentTrace id=%s", trace_id)
        return trace

    def delete_agent_trace(self, trace_id: UUID, run_id: UUID | None = None) -> bool:
        """Permanently delete an agent trace."""
        if run_id is not None:
            trace = self.get_agent_trace_for_run(run_id, trace_id)
        else:
            trace = self.get_agent_trace(trace_id)

        self.db.delete(trace)
        self._commit()
        logger.info("Deleted AgentTrace id=%s", trace_id)
        return True

    # ── Prompt Log methods ─────────────────────────────────────────────────────

    def create_prompt_log(self, payload: PromptLogCreate, run_id: UUID | None = None) -> PromptLog:
        """Create a new prompt log record."""
        effective_run_id = run_id if run_id is not None else payload.run_id
        self._verify_run(effective_run_id)
        self._verify_book_optional(payload.book_id)

        log = PromptLog(
            run_id=effective_run_id,
            book_id=payload.book_id,
            agent_name=self._enum_to_str(payload.agent_name),
            model_name=payload.model_name,
            prompt_name=payload.prompt_name,
            prompt_text=payload.prompt_text,
            input_payload=payload.input_payload,
            output_payload=payload.output_payload,
        )
        self.db.add(log)
        self._commit()
        self.db.refresh(log)
        logger.info("Created PromptLog id=%s for run_id=%s", log.id, effective_run_id)
        return log

    def get_prompt_log(self, prompt_log_id: UUID) -> PromptLog:
        """Fetch a prompt log by id."""
        log = self.db.get(PromptLog, prompt_log_id)
        if log is None:
            raise NotFoundError(
                message="Prompt log not found",
                code="prompt_log_not_found",
                details={"prompt_log_id": str(prompt_log_id)},
            )
        return log

    def get_prompt_log_for_run(self, run_id: UUID, prompt_log_id: UUID) -> PromptLog:
        """Fetch a prompt log scoped to a run."""
        self._verify_run(run_id)
        log = (
            self.db.query(PromptLog)
            .filter(PromptLog.id == prompt_log_id, PromptLog.run_id == run_id)
            .first()
        )
        if log is None:
            raise NotFoundError(
                message="Prompt log not found in this run",
                code="prompt_log_not_found",
                details={"prompt_log_id": str(prompt_log_id), "run_id": str(run_id)},
            )
        return log

    def list_prompt_logs(
        self,
        run_id: UUID | None = None,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        agent_name: str | None = None,
        model_name: str | None = None,
        prompt_name: str | None = None,
        search: str | None = None,
    ) -> tuple[list[PromptLog], int]:
        """List paginated prompt logs sorted newest-first by created_at."""
        query = self.db.query(PromptLog)
        if run_id is not None:
            query = query.filter(PromptLog.run_id == run_id)
        if book_id is not None:
            query = query.filter(PromptLog.book_id == book_id)
        if agent_name is not None:
            query = query.filter(PromptLog.agent_name == self._enum_to_str(agent_name))
        if model_name is not None:
            query = query.filter(PromptLog.model_name == model_name)
        if prompt_name is not None:
            query = query.filter(PromptLog.prompt_name == prompt_name)
        if search is not None:
            query = query.filter(PromptLog.prompt_text.ilike(f"%{search}%"))

        query = query.order_by(desc(PromptLog.created_at))
        return self._paginate(query, page, page_size)

    def update_prompt_log(self, prompt_log_id: UUID, payload: PromptLogUpdate, run_id: UUID | None = None) -> PromptLog:
        """Apply a partial update to a prompt log."""
        if run_id is not None:
            log = self.get_prompt_log_for_run(run_id, prompt_log_id)
        else:
            log = self.get_prompt_log(prompt_log_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(log, field, value)

        self._commit()
        self.db.refresh(log)
        logger.info("Updated PromptLog id=%s", prompt_log_id)
        return log

    def delete_prompt_log(self, prompt_log_id: UUID, run_id: UUID | None = None) -> bool:
        """Permanently delete a prompt log."""
        if run_id is not None:
            log = self.get_prompt_log_for_run(run_id, prompt_log_id)
        else:
            log = self.get_prompt_log(prompt_log_id)

        self.db.delete(log)
        self._commit()
        logger.info("Deleted PromptLog id=%s", prompt_log_id)
        return True

    # ── Memory I/O Log methods ─────────────────────────────────────────────────

    def create_memory_io_log(self, payload: MemoryIOLogCreate, run_id: UUID | None = None) -> MemoryIOLog:
        """Create a new memory operation log."""
        effective_run_id = run_id if run_id is not None else payload.run_id
        if effective_run_id is not None:
            self._verify_run(effective_run_id)
        self._verify_book_optional(payload.book_id)

        log = MemoryIOLog(
            run_id=effective_run_id,
            book_id=payload.book_id,
            agent_name=self._enum_to_str(payload.agent_name),
            operation=self._enum_to_str(payload.operation),
            memory_type=payload.memory_type,
            payload=payload.payload,
        )
        self.db.add(log)
        self._commit()
        self.db.refresh(log)
        logger.info("Created MemoryIOLog id=%s for run_id=%s", log.id, effective_run_id)
        return log

    def get_memory_io_log(self, log_id: UUID) -> MemoryIOLog:
        """Fetch a memory IO log by id."""
        log = self.db.get(MemoryIOLog, log_id)
        if log is None:
            raise NotFoundError(
                message="Memory IO log not found",
                code="memory_io_log_not_found",
                details={"log_id": str(log_id)},
            )
        return log

    def get_memory_io_log_for_run(self, run_id: UUID, log_id: UUID) -> MemoryIOLog:
        """Fetch a memory IO log scoped to a run."""
        self._verify_run(run_id)
        log = (
            self.db.query(MemoryIOLog)
            .filter(MemoryIOLog.id == log_id, MemoryIOLog.run_id == run_id)
            .first()
        )
        if log is None:
            raise NotFoundError(
                message="Memory IO log not found in this run",
                code="memory_io_log_not_found",
                details={"log_id": str(log_id), "run_id": str(run_id)},
            )
        return log

    def list_memory_io_logs(
        self,
        run_id: UUID | None = None,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        agent_name: str | None = None,
        operation: str | None = None,
        memory_type: str | None = None,
    ) -> tuple[list[MemoryIOLog], int]:
        """List paginated memory IO logs sorted newest-first by created_at."""
        query = self.db.query(MemoryIOLog)
        if run_id is not None:
            query = query.filter(MemoryIOLog.run_id == run_id)
        if book_id is not None:
            query = query.filter(MemoryIOLog.book_id == book_id)
        if agent_name is not None:
            query = query.filter(MemoryIOLog.agent_name == self._enum_to_str(agent_name))
        if operation is not None:
            query = query.filter(MemoryIOLog.operation == self._enum_to_str(operation))
        if memory_type is not None:
            query = query.filter(MemoryIOLog.memory_type == memory_type)

        query = query.order_by(desc(MemoryIOLog.created_at))
        return self._paginate(query, page, page_size)

    def delete_memory_io_log(self, log_id: UUID, run_id: UUID | None = None) -> bool:
        """Permanently delete a memory IO log."""
        if run_id is not None:
            log = self.get_memory_io_log_for_run(run_id, log_id)
        else:
            log = self.get_memory_io_log(log_id)

        self.db.delete(log)
        self._commit()
        logger.info("Deleted MemoryIOLog id=%s", log_id)
        return True

    # ── Token Cost Ledger methods ──────────────────────────────────────────────

    def create_token_cost(self, payload: TokenCostLedgerCreate, run_id: UUID | None = None) -> TokenCostLedger:
        """Create a new token cost ledger record."""
        effective_run_id = run_id if run_id is not None else payload.run_id
        if effective_run_id is not None:
            self._verify_run(effective_run_id)
        self._verify_book_optional(payload.book_id)

        total = payload.total_tokens if payload.total_tokens is not None else (payload.input_tokens + payload.output_tokens)

        ledger = TokenCostLedger(
            run_id=effective_run_id,
            book_id=payload.book_id,
            agent_name=self._enum_to_str(payload.agent_name),
            model_name=payload.model_name,
            input_tokens=payload.input_tokens,
            output_tokens=payload.output_tokens,
            total_tokens=total,
            estimated_cost=payload.estimated_cost,
            currency=payload.currency or "USD",
            ledger_metadata=payload.ledger_metadata,
        )
        self.db.add(ledger)
        self._commit()
        self.db.refresh(ledger)
        logger.info("Created TokenCostLedger id=%s for run_id=%s", ledger.id, effective_run_id)
        return ledger

    def get_token_cost(self, cost_id: UUID) -> TokenCostLedger:
        """Fetch a token cost entry by id."""
        ledger = self.db.get(TokenCostLedger, cost_id)
        if ledger is None:
            raise NotFoundError(
                message="Token cost ledger entry not found",
                code="token_cost_not_found",
                details={"cost_id": str(cost_id)},
            )
        return ledger

    def get_token_cost_for_run(self, run_id: UUID, cost_id: UUID) -> TokenCostLedger:
        """Fetch a token cost entry scoped to a run."""
        self._verify_run(run_id)
        ledger = (
            self.db.query(TokenCostLedger)
            .filter(TokenCostLedger.id == cost_id, TokenCostLedger.run_id == run_id)
            .first()
        )
        if ledger is None:
            raise NotFoundError(
                message="Token cost ledger entry not found in this run",
                code="token_cost_not_found",
                details={"cost_id": str(cost_id), "run_id": str(run_id)},
            )
        return ledger

    def list_token_costs(
        self,
        run_id: UUID | None = None,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        agent_name: str | None = None,
        model_name: str | None = None,
    ) -> tuple[list[TokenCostLedger], int]:
        """List paginated token costs sorted newest-first by created_at."""
        query = self.db.query(TokenCostLedger)
        if run_id is not None:
            query = query.filter(TokenCostLedger.run_id == run_id)
        if book_id is not None:
            query = query.filter(TokenCostLedger.book_id == book_id)
        if agent_name is not None:
            query = query.filter(TokenCostLedger.agent_name == self._enum_to_str(agent_name))
        if model_name is not None:
            query = query.filter(TokenCostLedger.model_name == model_name)

        query = query.order_by(desc(TokenCostLedger.created_at))
        return self._paginate(query, page, page_size)

    def update_token_cost(self, cost_id: UUID, payload: TokenCostLedgerUpdate, run_id: UUID | None = None) -> TokenCostLedger:
        """Apply a partial update to a token cost entry, recomputing total_tokens if needed."""
        if run_id is not None:
            ledger = self.get_token_cost_for_run(run_id, cost_id)
        else:
            ledger = self.get_token_cost(cost_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ledger, field, value)

        # Recompute total_tokens if inputs/outputs changed and not explicitly provided
        if "input_tokens" in update_data or "output_tokens" in update_data:
            if "total_tokens" not in update_data:
                ledger.total_tokens = ledger.input_tokens + ledger.output_tokens

        self._commit()
        self.db.refresh(ledger)
        logger.info("Updated TokenCostLedger id=%s", cost_id)
        return ledger

    def delete_token_cost(self, cost_id: UUID, run_id: UUID | None = None) -> bool:
        """Permanently delete a token cost entry."""
        if run_id is not None:
            ledger = self.get_token_cost_for_run(run_id, cost_id)
        else:
            ledger = self.get_token_cost(cost_id)

        self.db.delete(ledger)
        self._commit()
        logger.info("Deleted TokenCostLedger id=%s", cost_id)
        return True

    # ── Trace Bundle & Cost Summary methods ─────────────────────────────────────

    def get_trace_bundle(self, run_id: UUID) -> TraceBundleResponse:
        """Compile complete traces for a specific run."""
        run = self._verify_run(run_id)

        traces = (
            self.db.query(AgentTrace)
            .filter(AgentTrace.run_id == run_id)
            .order_by(asc(AgentTrace.created_at))
            .all()
        )
        prompt_logs = (
            self.db.query(PromptLog)
            .filter(PromptLog.run_id == run_id)
            .order_by(desc(PromptLog.created_at))
            .all()
        )
        memory_logs = (
            self.db.query(MemoryIOLog)
            .filter(MemoryIOLog.run_id == run_id)
            .order_by(desc(MemoryIOLog.created_at))
            .all()
        )
        costs = (
            self.db.query(TokenCostLedger)
            .filter(TokenCostLedger.run_id == run_id)
            .order_by(desc(TokenCostLedger.created_at))
            .all()
        )

        return TraceBundleResponse(
            run_id=run_id,
            book_id=run.book_id,
            traces=traces,
            prompt_logs=prompt_logs,
            memory_io_logs=memory_logs,
            token_cost_ledger=costs,
            total_prompt_logs=len(prompt_logs),
            total_trace_records=len(traces),
            total_memory_io_records=len(memory_logs),
            total_token_cost_records=len(costs),
            status="ready",
            message="Trace bundle successfully compiled.",
        )

    def get_run_cost_summary(self, run_id: UUID) -> RunCostSummaryResponse:
        """Aggregate token cost totals for a specific run."""
        run = self._verify_run(run_id)

        entries = (
            self.db.query(TokenCostLedger)
            .filter(TokenCostLedger.run_id == run_id)
            .all()
        )

        total_input = 0
        total_output = 0
        total_tok = 0
        total_cost = 0.0

        model_breakdown = {}

        for entry in entries:
            total_input += entry.input_tokens
            total_output += entry.output_tokens
            total_tok += entry.total_tokens
            if entry.estimated_cost is not None:
                total_cost += float(entry.estimated_cost)

            model = entry.model_name
            if model not in model_breakdown:
                model_breakdown[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost": 0.0,
                }
            model_breakdown[model]["input_tokens"] += entry.input_tokens
            model_breakdown[model]["output_tokens"] += entry.output_tokens
            model_breakdown[model]["total_tokens"] += entry.total_tokens
            if entry.estimated_cost is not None:
                model_breakdown[model]["estimated_cost"] += float(entry.estimated_cost)

        return RunCostSummaryResponse(
            run_id=run_id,
            book_id=run.book_id,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tok,
            total_estimated_cost=total_cost,
            currency="USD",
            model_breakdown=model_breakdown,
        )
