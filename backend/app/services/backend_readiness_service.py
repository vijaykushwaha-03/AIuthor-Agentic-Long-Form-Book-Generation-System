"""
AIuthor Backend — Backend Readiness Service.
Provides final assessment-readiness checks for database, agents, prompts, and APIs.
"""
from __future__ import annotations

import logging
from uuid import UUID
from pathlib import Path
import json
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.pgvector_check import get_pgvector_status
from app.models import BookProject, BookRun, Chapter, BookSection, ExportFile
from app.models.memory import FactRegistry, ConceptBible, CharacterBible, CallbackIndex, ToneFingerprint, DecisionLog
from app.models.observability import AgentTrace, PromptLog, TokenCostLedger
from app.agents.prompt_registry import PromptRegistry
from app.workflows.schemas import (
    BackendReadinessCheckItem,
    BackendReadinessReportRequest,
    BackendReadinessReportResponse,
)

logger = logging.getLogger(__name__)

class BackendReadinessService:
    """
    Orchestrates health checks and compliance validations for the backend assessment.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def _check_database_tables(self) -> list[BackendReadinessCheckItem]:
        checks = []
        inspector = inspect(self.db.bind)
        existing_tables = inspector.get_table_names()

        required_tables = [
            "book_projects",
            "book_runs",
            "chapters",
            "book_sections",
            "source_documents",
            "document_chunks",
            "fact_registry",
            "concept_bible",
            "character_bible",
            "callback_index",
            "tone_fingerprints",
            "decision_log",
            "agent_traces",
            "prompt_logs",
            "memory_io_logs",
            "token_cost_ledger",
            "eval_results",
            "export_files",
        ]

        for table in required_tables:
            if table in existing_tables:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"db_table_{table}",
                        category="database",
                        status="pass",
                        message=f"Database table '{table}' is verified and present.",
                        details={"table_name": table}
                    )
                )
            else:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"db_table_{table}",
                        category="database",
                        status="fail",
                        message=f"Database table '{table}' is missing from the database schema.",
                        details={"table_name": table}
                    )
                )
        return checks

    def _check_pgvector_readiness(self) -> list[BackendReadinessCheckItem]:
        checks = []
        status_info = get_pgvector_status(self.db)
        is_postgres = self.db.bind.dialect.name == "postgresql"

        if not is_postgres:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="pgvector_readiness",
                    category="database",
                    status="skipped",
                    message="Non-PostgreSQL dialect connected (SQLite in use). pgvector extension check skipped.",
                    details={"dialect": self.db.bind.dialect.name, "pgvector_available": False}
                )
            )
        else:
            if status_info["available"]:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="pgvector_readiness",
                        category="database",
                        status="pass",
                        message="pgvector extension is installed and ready in PostgreSQL.",
                        details=status_info
                    )
                )
            else:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="pgvector_readiness",
                        category="database",
                        status="warning",
                        message="pgvector extension is missing in PostgreSQL. Vector searches will fallback to cosine calculations.",
                        details=status_info
                    )
                )
        return checks

    def _check_agent_registry(self) -> list[BackendReadinessCheckItem]:
        checks = []
        required_agents = [
            "planner",
            "researcher",
            "writer",
            "humanizer",
            "editor",
            "fact_checker",
            "memory_keeper",
            "assembler",
        ]

        registry = PromptRegistry()
        try:
            available_templates = registry.list_templates()
            for agent in required_agents:
                if agent in available_templates:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name=f"agent_registry_{agent}",
                            category="agents",
                            status="pass",
                            message=f"Agent '{agent}' prompt template is present in the prompt registry.",
                            details={"agent": agent}
                        )
                    )
                else:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name=f"agent_registry_{agent}",
                            category="agents",
                            status="fail",
                            message=f"Agent '{agent}' prompt template is missing from prompt registry.",
                            details={"agent": agent}
                        )
                    )
        except Exception as e:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="agent_registry_load",
                    category="agents",
                    status="fail",
                    message=f"Failed to scan prompt registry: {e}",
                    details={"error": str(e)}
                )
            )
        return checks

    def _check_prompt_registry(self) -> list[BackendReadinessCheckItem]:
        checks = []
        required_agents = [
            "planner",
            "researcher",
            "writer",
            "humanizer",
            "editor",
            "fact_checker",
            "memory_keeper",
            "assembler",
        ]

        registry = PromptRegistry()
        for agent in required_agents:
            try:
                template = registry.get_template(agent)
                version = registry.get_version(agent)
                if template:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name=f"prompt_template_{agent}",
                            category="prompts",
                            status="pass",
                            message=f"Prompt template for '{agent}' loaded successfully (version: {version}).",
                            details={"agent": agent, "version": version, "template_length": len(template)}
                        )
                    )
                else:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name=f"prompt_template_{agent}",
                            category="prompts",
                            status="fail",
                            message=f"Prompt template for '{agent}' is empty.",
                            details={"agent": agent}
                        )
                    )
            except Exception as e:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"prompt_template_{agent}",
                        category="prompts",
                        status="fail",
                        message=f"Prompt template for '{agent}' failed to load: {e}",
                        details={"agent": agent, "error": str(e)}
                    )
                )
        return checks

    def _check_workflows(self) -> list[BackendReadinessCheckItem]:
        from app.workflows.graph import REGISTERED_WORKFLOWS
        checks = []
        expected_workflows = {
            "mini_book_pipeline": 5,
            "full_agent_pipeline": 8,
        }

        for workflow_name, expected_node_count in expected_workflows.items():
            info = REGISTERED_WORKFLOWS.get(workflow_name)
            if info is None:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"workflow_{workflow_name}",
                        category="workflows",
                        status="fail",
                        message=f"Workflow '{workflow_name}' is not registered.",
                        details={"workflow_name": workflow_name}
                    )
                )
            else:
                node_count = len(info.nodes)
                if node_count == expected_node_count:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name=f"workflow_{workflow_name}",
                            category="workflows",
                            status="pass",
                            message=f"Workflow '{workflow_name}' is registered and verified with {node_count} nodes.",
                            details={"workflow_name": workflow_name, "node_count": node_count}
                        )
                    )
                else:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name=f"workflow_{workflow_name}",
                            category="workflows",
                            status="fail",
                            message=f"Workflow '{workflow_name}' has incorrect node count. Expected {expected_node_count}, got {node_count}.",
                            details={"workflow_name": workflow_name, "expected": expected_node_count, "actual": node_count}
                        )
                    )
        return checks

    def _check_api_inventory(self) -> list[BackendReadinessCheckItem]:
        from app.main import app
        checks = []
        expected_paths = [
            "/api/books",
            "/api/books/{book_id}/workflow/dev-run-real",
            "/api/books/{book_id}/chapters/generate/dev-run-real",
            "/api/books/{book_id}/chapters/insert-repair/dev-run-real",
            "/api/books/{book_id}/memory/extract/dev-run-real",
            "/api/books/{book_id}/memory/continuity-pack",
            "/api/books/{book_id}/assemble",
            "/api/books/{book_id}/exports/generate",
            "/api/books/{book_id}/reports/evaluation",
            "/api/reports/prompt-dossier",
            "/api/books/{book_id}/delivery-bundle",
        ]

        route_paths = [route.path for route in app.routes if hasattr(route, "path")]

        for path in expected_paths:
            if path in route_paths:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"api_route_{path}",
                        category="api",
                        status="pass",
                        message=f"API endpoint '{path}' is registered in routing map.",
                        details={"path": path}
                    )
                )
            else:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"api_route_{path}",
                        category="api",
                        status="fail",
                        message=f"API endpoint '{path}' is missing from routing map.",
                        details={"path": path}
                    )
                )
        return checks

    def _check_safety_gates(self) -> list[BackendReadinessCheckItem]:
        checks = []
        settings = get_settings()

        gates = {
            "enable_real_agent_test_api": settings.enable_real_agent_test_api,
            "enable_real_workflow_test_api": settings.enable_real_workflow_test_api,
            "enable_real_memory_test_api": settings.enable_real_memory_test_api,
        }

        for name, value in gates.items():
            if value is False:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"safety_gate_{name}",
                        category="safety",
                        status="pass",
                        message=f"Safety gate '{name}' is disabled by default.",
                        details={"gate_name": name, "enabled": False}
                    )
                )
            else:
                checks.append(
                    BackendReadinessCheckItem(
                        check_name=f"safety_gate_{name}",
                        category="safety",
                        status="warning",
                        message=f"Safety gate '{name}' is enabled (danger of live API hits).",
                        details={"gate_name": name, "enabled": True}
                    )
                )
        return checks

    def _check_project_artifacts(self, book_id: UUID, run_id: UUID | None = None) -> list[BackendReadinessCheckItem]:
        checks = []

        book = self.db.get(BookProject, book_id)
        if not book:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_exists",
                    category="artifacts",
                    status="fail",
                    message=f"Book project with ID {book_id} not found in database.",
                    details={"book_id": str(book_id)}
                )
            )
            return checks

        # Chapters
        chapters = self.db.query(Chapter).filter(Chapter.book_id == book_id).all()
        if not chapters:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_chapters",
                    category="artifacts",
                    status="warning",
                    message="No chapters exist for this book project.",
                    details={}
                )
            )
        else:
            has_text = any(c.final_text or c.draft_text for c in chapters)
            status = "pass" if has_text else "warning"
            msg = f"Found {len(chapters)} chapter(s) with generated text." if has_text else f"Found {len(chapters)} chapter(s) but no text has been generated yet."
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_chapters",
                    category="artifacts",
                    status=status,
                    message=msg,
                    details={"chapter_count": len(chapters), "has_text": has_text}
                )
            )

        # Memory
        facts = self.db.query(FactRegistry).filter(FactRegistry.book_id == book_id).count()
        concepts = self.db.query(ConceptBible).filter(ConceptBible.book_id == book_id).count()
        total_mem = facts + concepts
        status = "pass" if total_mem > 0 else "warning"
        checks.append(
            BackendReadinessCheckItem(
                check_name="project_memory_records",
                category="artifacts",
                status=status,
                message=f"Found {total_mem} memory records (facts/concepts) in database.",
                details={"facts": facts, "concepts": concepts}
            )
        )

        # Exports
        exports = self.db.query(ExportFile).filter(ExportFile.book_id == book_id).all()
        docx_exports = [e for e in exports if e.export_type == "docx"]
        if docx_exports:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_export_records",
                    category="artifacts",
                    status="pass",
                    message="DOCX export records successfully verified.",
                    details={"docx_count": len(docx_exports)}
                )
            )
        else:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_export_records",
                    category="artifacts",
                    status="warning",
                    message="No DOCX export files found for this book project.",
                    details={}
                )
            )

        # Delivery Manifest
        settings = get_settings()
        book_dir = Path(settings.delivery_output_dir) / str(book_id)
        manifest_path = next(book_dir.glob("**/manifest.json"), None) if book_dir.exists() else None
        if manifest_path and manifest_path.exists():
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_delivery_manifest",
                    category="artifacts",
                    status="pass",
                    message="Delivery bundle manifest.json verified on disk.",
                    details={"path": str(manifest_path)}
                )
            )
        else:
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_delivery_manifest",
                    category="artifacts",
                    status="warning",
                    message="No delivery bundle manifest found on disk.",
                    details={}
                )
            )

        # Traces
        if run_id:
            traces_count = self.db.query(AgentTrace).filter(AgentTrace.run_id == run_id).count()
            status = "pass" if traces_count > 0 else "warning"
            checks.append(
                BackendReadinessCheckItem(
                    check_name="project_run_traces",
                    category="artifacts",
                    status=status,
                    message=f"Found {traces_count} workflow trace steps for the specified run ID.",
                    details={"run_id": str(run_id), "trace_steps": traces_count}
                )
            )

        return checks

    def _build_markdown_report(self, checks: list[BackendReadinessCheckItem]) -> str:
        lines = []
        lines.append("# AIuthor Backend Readiness Report\n")

        total = len(checks)
        passed = sum(1 for c in checks if c.status == "pass")
        warning = sum(1 for c in checks if c.status == "warning")
        failed = sum(1 for c in checks if c.status == "fail")
        skipped = sum(1 for c in checks if c.status == "skipped")

        overall = "pass"
        if failed > 0:
            overall = "fail"
        elif warning > 0:
            overall = "warning"

        lines.append("## Summary")
        lines.append(f"- **Overall Assessment Readiness**: **{overall.upper()}**")
        lines.append(f"- **Total Checks**: {total}")
        lines.append(f"- **Passed Checks**: {passed}")
        lines.append(f"- **Warnings**: {warning}")
        lines.append(f"- **Failures**: {failed}")
        lines.append(f"- **Skipped Checks**: {skipped}\n")

        lines.append("## Scorecard")
        lines.append("| Check Name | Category | Status | Message |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for c in checks:
            lines.append(f"| {c.check_name} | {c.category} | {c.status.upper()} | {c.message} |")
        lines.append("")

        categories = ["database", "agents", "prompts", "workflows", "api", "safety", "artifacts"]
        display_names = {
            "database": "Database Checks",
            "agents": "Agent Checks",
            "prompts": "Prompt Checks",
            "workflows": "Workflow Checks",
            "api": "API Checks",
            "safety": "Safety Checks",
            "artifacts": "Project Artifact Checks",
        }

        for cat in categories:
            cat_checks = [c for c in checks if c.category == cat]
            if not cat_checks:
                continue
            lines.append(f"## {display_names[cat]}")
            for c in cat_checks:
                lines.append(f"- **{c.check_name}** ({c.status.upper()}): {c.message}")
            lines.append("")

        lines.append("## Final Recommendation")
        if failed > 0:
            lines.append("> [!CAUTION]")
            lines.append("> Severe configuration or code failures detected. The backend is NOT ready for demo or submission. Please address failed checks immediately.")
        elif warning > 0:
            lines.append("> [!WARNING]")
            lines.append("> Minor warnings present. Word counts might be low, vector fallback active, or safety parameters enabled. Review details before final submission.")
        else:
            lines.append("> [!TIP]")
            lines.append("> All checks passed successfully. The backend services are fully assessment-ready, stable, and ready for deployment.")

        return "\n".join(lines)

    def run_readiness_report(self, request: BackendReadinessReportRequest) -> BackendReadinessReportResponse:
        checks = []

        if request.include_database_checks:
            checks.extend(self._check_database_tables())
            checks.extend(self._check_pgvector_readiness())
        if request.include_agent_checks:
            checks.extend(self._check_agent_registry())
        if request.include_workflow_checks:
            checks.extend(self._check_prompt_registry())
            checks.extend(self._check_workflows())
        if request.include_api_checks:
            checks.extend(self._check_api_inventory())
        if request.include_safety_checks:
            checks.extend(self._check_safety_gates())
        if request.book_id:
            checks.extend(self._check_project_artifacts(request.book_id, request.run_id))

        total_checks = len(checks)
        pass_count = sum(1 for c in checks if c.status == "pass")
        warning_count = sum(1 for c in checks if c.status == "warning")
        fail_count = sum(1 for c in checks if c.status == "fail")
        skipped_count = sum(1 for c in checks if c.status == "skipped")

        overall_status = "pass"
        if fail_count > 0:
            overall_status = "fail"
        elif warning_count > 0:
            overall_status = "warning"

        markdown_report = self._build_markdown_report(checks)

        return BackendReadinessReportResponse(
            status=overall_status,
            total_checks=total_checks,
            pass_count=pass_count,
            warning_count=warning_count,
            fail_count=fail_count,
            skipped_count=skipped_count,
            checks=checks,
            markdown_report=markdown_report,
            metadata=request.metadata,
        )
