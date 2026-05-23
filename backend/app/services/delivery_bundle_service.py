"""
AIuthor Backend — Delivery Bundle Service.
Assembles and writes assessment-ready delivery artifacts to disk, exporting a manifest.
"""
from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from uuid import UUID
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import BookProject, ExportFile
from app.models.memory import FactRegistry, ConceptBible, CharacterBible, CallbackIndex, ToneFingerprint, DecisionLog
from app.models.observability import AgentTrace, TokenCostLedger
from app.workflows.schemas import (
    DeliveryBundleRequest,
    DeliveryArtifactItem,
    DeliveryBundleResponse,
    EvaluationReportRequest,
    PromptDossierRequest,
    ContinuityPackRequest,
)
from app.services.evaluation_report_service import EvaluationReportService
from app.services.prompt_dossier_service import PromptDossierService
from app.services.continuity_pack_service import ContinuityPackService
from app.services.workflow_observability_service import WorkflowObservabilityService
from app.services.export_service import ExportService

logger = logging.getLogger(__name__)

class DeliveryBundleService:
    """
    Service responsible for packaging and writing final assessment documentation delivery bundles.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.eval_report_service = EvaluationReportService(db)
        self.prompt_dossier_service = PromptDossierService()
        self.continuity_pack_service = ContinuityPackService(db)
        self.workflow_observability_service = WorkflowObservabilityService(db)
        self.export_service = ExportService(db)

    def _get_output_dir(self, book_id: UUID, run_id: UUID | None = None) -> Path:
        settings = get_settings()
        run_folder = str(run_id) if run_id else "manual"
        # Relative path resolved under backend root
        return Path(settings.delivery_output_dir) / str(book_id) / run_folder

    def _write_text_artifact(self, output_dir: Path, filename: str, content: str, artifact_type: str) -> DeliveryArtifactItem:
        file_path = output_dir / filename
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            file_size_bytes = file_path.stat().st_size
            return DeliveryArtifactItem(
                artifact_type=artifact_type,
                status="ready",
                file_name=filename,
                file_path=str(file_path.absolute().as_posix()),
                file_size_bytes=file_size_bytes,
                metadata={},
            )
        except Exception as e:
            logger.error("Failed to write artifact %s to %s: %s", artifact_type, file_path, e)
            return DeliveryArtifactItem(
                artifact_type=artifact_type,
                status="failed",
                file_name=filename,
                error_message=str(e),
                metadata={},
            )

    def generate_architecture_summary(self, book_id: UUID, run_id: UUID | None = None) -> str:
        lines = []
        lines.append("# AIuthor Architecture Summary\n")
        lines.append(f"- **Book Project ID**: `{book_id}`")
        if run_id:
            lines.append(f"- **Workflow Run ID**: `{run_id}`")
        lines.append("")
        lines.append("This document provides an overview of the AIuthor Long-Form Book Generation System architecture.\n")
        lines.append("## Core Backend Stack")
        lines.append("- **FastAPI Backend**: Provides asynchronous, type-safe API routing with automatic OpenAPI generation.")
        lines.append("- **PostgreSQL 16 + pgvector**: Stores book projects, chapters, memory registries, and pgvector-backed semantic chunk embeddings.")
        lines.append("- **SQLAlchemy 2.0 & Alembic**: Implements strong model typing and manages database migration schemas.\n")
        lines.append("## Cognitive Architecture & Workflows")
        lines.append("- **Agentic Orchestration**: Governed by structured prompts for 8 core agents (Planner, Researcher, Writer, Humanizer, Editor, Fact Checker, Memory Keeper, Assembler).")
        lines.append("- **LangGraph Pipelines**: Manages conditional branching and state verification during multi-agent book runs.")
        lines.append("- **RAG Retrieval Engine**: Performs hybrid keyword-semantic queries against pre-registered source reference materials.\n")
        lines.append("## Observability & Quality Assurance")
        lines.append("- **Execution Tracing**: Detailed AgentTrace logs track inputs, outputs, errors, and agent statuses sequentially.")
        lines.append("- **Token & Cost Ledgers**: Records model parameters and billing counts per request for auditing.")
        lines.append("- **Automated Evaluations**: Validates structural requirements including chapter sequencing and memory continuity.")
        return "\n".join(lines)

    def generate_memory_report(self, book_id: UUID) -> str:
        req = ContinuityPackRequest(
            book_id=book_id,
            include_facts=True,
            include_concepts=True,
            include_characters=True,
            include_callbacks=True,
            include_tone=True,
            include_decisions=True,
            max_items_per_type=100,
            max_chars=50000,
        )
        res = self.continuity_pack_service.build_continuity_pack(req)

        lines = []
        lines.append("# AIuthor Memory and Lore Report\n")
        lines.append("This report lists the structured knowledge and continuity context currently active in the database for the book project.\n")
        lines.append("## Memory Overview")
        lines.append(f"- **Facts Count**: {len(res.facts)}")
        lines.append(f"- **Concepts Count**: {len(res.concepts)}")
        lines.append(f"- **Characters Count**: {len(res.characters)}")
        lines.append(f"- **Callbacks Count**: {len(res.callbacks)}")
        lines.append(f"- **Tone Fingerprints**: {len(res.tone_fingerprints)}")
        lines.append(f"- **Engineering Decisions**: {len(res.decisions)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(res.continuity_text)
        return "\n".join(lines)

    def generate_trace_summary(self, book_id: UUID, run_id: UUID | None = None) -> str:
        trace_query = self.db.query(AgentTrace).filter(AgentTrace.book_id == book_id)
        if run_id:
            trace_query = trace_query.filter(AgentTrace.run_id == run_id)
        traces = trace_query.order_by(AgentTrace.created_at.asc()).all()

        ledger_query = self.db.query(TokenCostLedger).filter(TokenCostLedger.book_id == book_id)
        if run_id:
            ledger_query = ledger_query.filter(TokenCostLedger.run_id == run_id)
        ledgers = ledger_query.all()

        total_input_tokens = sum(l.input_tokens for l in ledgers if l.input_tokens is not None)
        total_output_tokens = sum(l.output_tokens for l in ledgers if l.output_tokens is not None)
        total_cost = sum(l.estimated_cost for l in ledgers if l.estimated_cost is not None)

        lines = []
        lines.append("# AIuthor Trace and Observability Summary\n")
        lines.append("## Trace Overview")
        lines.append(f"- **Total Logged Trace Steps**: {len(traces)}")
        lines.append(f"- **Total Token Cost Ledger Rows**: {len(ledgers)}")
        lines.append(f"- **Estimated Total Cost**: ${total_cost:.5f}")
        lines.append(f"- **Total Input Tokens**: {total_input_tokens}")
        lines.append(f"- **Total Output Tokens**: {total_output_tokens}\n")

        lines.append("## Node Trace Log")
        lines.append("| Agent Name | Status | Duration | Created At |")
        lines.append("| :--- | :--- | :--- | :--- |")
        if not traces:
            lines.append("| N/A | No traces logged | N/A | N/A |")
        else:
            for t in traces:
                duration_str = t.trace_metadata.get("duration_ms", "N/A") if t.trace_metadata else "N/A"
                if duration_str != "N/A":
                    duration_str = f"{duration_str} ms"
                lines.append(f"| {t.agent_name or 'Unknown'} | {t.status.upper()} | {duration_str} | {t.created_at.isoformat()} |")

        return "\n".join(lines)

    def generate_export_summary(self, book_id: UUID, run_id: UUID | None = None) -> str:
        query = self.db.query(ExportFile).filter(ExportFile.book_id == book_id)
        if run_id:
            query = query.filter(ExportFile.run_id == run_id)
        exports = query.all()

        lines = []
        lines.append("# AIuthor Export Summary\n")
        lines.append("This document summarizes the manuscript exports generated for this book project.\n")
        lines.append("## Active Exports")
        lines.append("| File Name | Format | Status | Path | Size |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        if not exports:
            lines.append("| N/A | No exports generated | N/A | N/A | N/A |")
        else:
            for e in exports:
                size_str = f"{e.export_metadata.get('file_size_bytes', 0)} bytes" if e.export_metadata else "Unknown"
                if size_str == "Unknown" and os.path.exists(e.file_path):
                    size_str = f"{os.path.getsize(e.file_path)} bytes"
                lines.append(f"| {e.file_name} | {e.export_type.upper()} | {e.status.upper()} | {e.file_path} | {size_str} |")

        return "\n".join(lines)

    def generate_delivery_bundle(self, request: DeliveryBundleRequest) -> DeliveryBundleResponse:
        output_dir = self._get_output_dir(request.book_id, request.run_id)
        if request.write_files:
            output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []

        # 1. Evaluation Report
        if request.include_eval_report:
            eval_req = EvaluationReportRequest(
                book_id=request.book_id,
                run_id=request.run_id,
                include_chapter_checks=True,
                include_export_checks=True,
                include_trace_checks=True,
                include_memory_checks=True,
                persist_eval_results=False, # Do not pollute DB evaluations during delivery write
            )
            eval_res = self.eval_report_service.generate_evaluation_report(eval_req)
            if request.write_files:
                art = self._write_text_artifact(output_dir, "evaluation_report.md", eval_res.markdown_report, "evaluation_report")
                artifacts.append(art)
            else:
                artifacts.append(DeliveryArtifactItem(artifact_type="evaluation_report", status="skipped_write"))

        # 2. Prompt Dossier
        if request.include_prompt_dossier:
            dossier_req = PromptDossierRequest(
                include_templates=True,
                include_versions=True,
                include_agent_roles=True,
                include_render_examples=True,
                metadata=request.metadata,
            )
            dossier_res = self.prompt_dossier_service.generate_prompt_dossier(dossier_req)
            if request.write_files:
                art = self._write_text_artifact(output_dir, "prompt_dossier.md", dossier_res.markdown_dossier, "prompt_dossier")
                artifacts.append(art)
            else:
                artifacts.append(DeliveryArtifactItem(artifact_type="prompt_dossier", status="skipped_write"))

        # 3. Architecture Summary
        if request.include_architecture_summary:
            arch_content = self.generate_architecture_summary(request.book_id, request.run_id)
            if request.write_files:
                art = self._write_text_artifact(output_dir, "architecture_summary.md", arch_content, "architecture_summary")
                artifacts.append(art)
            else:
                artifacts.append(DeliveryArtifactItem(artifact_type="architecture_summary", status="skipped_write"))

        # 4. Memory Report
        if request.include_memory_report:
            mem_content = self.generate_memory_report(request.book_id)
            if request.write_files:
                art = self._write_text_artifact(output_dir, "memory_report.md", mem_content, "memory_report")
                artifacts.append(art)
            else:
                artifacts.append(DeliveryArtifactItem(artifact_type="memory_report", status="skipped_write"))

        # 5. Trace Summary
        if request.include_trace_summary:
            trace_content = self.generate_trace_summary(request.book_id, request.run_id)
            if request.write_files:
                art = self._write_text_artifact(output_dir, "trace_summary.md", trace_content, "trace_summary")
                artifacts.append(art)
            else:
                artifacts.append(DeliveryArtifactItem(artifact_type="trace_summary", status="skipped_write"))

        # 6. Export Summary
        if request.include_export_summary:
            export_content = self.generate_export_summary(request.book_id, request.run_id)
            if request.write_files:
                art = self._write_text_artifact(output_dir, "export_summary.md", export_content, "export_summary")
                artifacts.append(art)
            else:
                artifacts.append(DeliveryArtifactItem(artifact_type="export_summary", status="skipped_write"))

        # Assemble manifest dict
        manifest = {
            "book_id": str(request.book_id),
            "run_id": str(request.run_id) if request.run_id else "manual",
            "generated_at": datetime.utcnow().isoformat(),
            "artifacts": [
                {
                    "artifact_type": art.artifact_type,
                    "status": art.status,
                    "file_name": art.file_name,
                    "file_path": art.file_path,
                    "file_size_bytes": art.file_size_bytes,
                    "error_message": art.error_message,
                }
                for art in artifacts
            ],
            "status": "success" if all(art.status in ("ready", "skipped_write") for art in artifacts) else "partial",
        }

        # Write manifest.json
        if request.write_files:
            manifest_str = json.dumps(manifest, indent=2, sort_keys=True)
            manifest_art = self._write_text_artifact(output_dir, "manifest.json", manifest_str, "manifest")
            # Update manifest entry in response artifacts if manifest written successfully
            artifacts.append(manifest_art)
            manifest["artifacts"].append({
                "artifact_type": manifest_art.artifact_type,
                "status": manifest_art.status,
                "file_name": manifest_art.file_name,
                "file_path": manifest_art.file_path,
                "file_size_bytes": manifest_art.file_size_bytes,
                "error_message": manifest_art.error_message,
            })

        return DeliveryBundleResponse(
            book_id=request.book_id,
            run_id=request.run_id,
            status=manifest["status"],
            artifacts=artifacts,
            manifest=manifest,
            metadata=request.metadata,
        )
