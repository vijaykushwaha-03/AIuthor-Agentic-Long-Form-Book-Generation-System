"""
AIuthor Backend — End-to-End Dry Run Service (Module 12.0).
Provides offline-safe execution validation of all system modules.
"""
from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter
from app.workflows.schemas import (
    BackendReadinessCheckItem,
    EndToEndDryRunRequest,
    EndToEndDryRunResponse,
    ChapterGenerationRequest,
    MemoryExtractionRequest,
    BookExportRequest,
    DeliveryBundleRequest,
)
from app.services.book_service import BookProjectService
from app.services.chapter_service import ChapterService
from app.services.chapter_generation_service import ChapterGenerationService
from app.services.memory_extraction_service import MemoryExtractionService
from app.services.document_export_service import DocumentExportService
from app.services.delivery_bundle_service import DeliveryBundleService

logger = logging.getLogger(__name__)


class EndToEndDryRunService:
    """
    Coordinates dry run validation tasks for backend submission readiness.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.book_service = BookProjectService(db)
        self.chapter_service = ChapterService(db)
        self.chapter_generation_service = ChapterGenerationService(db)
        self.memory_extraction_service = MemoryExtractionService(db)
        self.document_export_service = DocumentExportService(db)
        self.delivery_bundle_service = DeliveryBundleService(db)

    def run_dry_run(self, request: EndToEndDryRunRequest) -> EndToEndDryRunResponse:
        """
        Executes a synchronous, offline-safe sequential dry run of the book pipeline.
        """
        book_id = None
        run_id = None
        chapter_ids: list[UUID] = []
        generated_chapter_count = 0
        memory_written_count = 0
        export_file_count = 0
        delivery_artifact_count = 0
        checks: list[BackendReadinessCheckItem] = []

        # 1. Create/Retrieve BookProject
        try:
            if request.create_sample_book:
                book = BookProject(
                    topic=request.topic,
                    genre=request.genre,
                    reader_profile="Technical professionals",
                    tone=request.tone,
                    target_chapters=request.max_chapters,
                    project_metadata={
                        "title": f"A Technical Guide on {request.topic}",
                        "subtitle": "Synthesized dry run manuscript",
                        "author": "Vijay Patel",
                        "module": "12.0",
                        "dry_run": True,
                        **(request.metadata or {}),
                    },
                    status="created",
                )
                self.db.add(book)
                self.db.commit()
                self.db.refresh(book)
                book_id = book.id
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_create_book",
                        category="artifacts",
                        status="pass",
                        message="Sample BookProject created successfully.",
                        details={"book_id": str(book_id)}
                    )
                )
            else:
                book = self.db.query(BookProject).order_by(BookProject.created_at.desc()).first()
                if book:
                    book_id = book.id
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name="dry_run_reuse_book",
                            category="artifacts",
                            status="pass",
                            message=f"Reusing existing BookProject with ID {book_id}.",
                            details={"book_id": str(book_id)}
                        )
                    )
                else:
                    book = BookProject(
                        topic=request.topic,
                        genre=request.genre,
                        reader_profile="Technical professionals",
                        tone=request.tone,
                        target_chapters=request.max_chapters,
                        project_metadata={
                            "title": f"A Technical Guide on {request.topic}",
                            "subtitle": "Auto-created fallback book project",
                            "author": "Vijay Patel",
                            "module": "12.0",
                            "dry_run": True,
                        },
                        status="created",
                    )
                    self.db.add(book)
                    self.db.commit()
                    self.db.refresh(book)
                    book_id = book.id
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name="dry_run_create_book_fallback",
                            category="artifacts",
                            status="pass",
                            message="Sample BookProject auto-created as fallback.",
                            details={"book_id": str(book_id)}
                        )
                    )
        except Exception as e:
            logger.exception("Dry run failed at BookProject setup step")
            checks.append(
                BackendReadinessCheckItem(
                    check_name="dry_run_book_setup",
                    category="artifacts",
                    status="fail",
                    message=f"BookProject setup failed: {e}",
                    details={"error": str(e)}
                )
            )

        # 2. Create sample chapters if requested
        if book_id and request.create_sample_chapters:
            try:
                for i in range(1, request.max_chapters + 1):
                    existing_ch = self.db.query(Chapter).filter_by(book_id=book_id, chapter_number=i).first()
                    if not existing_ch:
                        ch = Chapter(
                            book_id=book_id,
                            chapter_number=i,
                            title=f"Introduction to {request.topic} (Part {i})",
                            summary=f"Overview of basic principles in {request.topic}.",
                            chapter_contract={
                                "chapter_number": i,
                                "title": f"Introduction to {request.topic} (Part {i})",
                                "purpose": "To introduce main concepts of this technical guide.",
                                "key_concepts": [request.topic],
                                "required_facts": ["The RAG concept is popular."],
                                "callback_opportunities": []
                            },
                            status="planned"
                        )
                        self.db.add(ch)
                        self.db.commit()
                        self.db.refresh(ch)
                        chapter_ids.append(ch.id)
                    else:
                        chapter_ids.append(existing_ch.id)

                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_create_chapters",
                        category="artifacts",
                        status="pass",
                        message=f"Sample chapters created/verified: {len(chapter_ids)} chapters.",
                        details={"chapter_ids": [str(cid) for cid in chapter_ids]}
                    )
                )
            except Exception as e:
                logger.exception("Dry run failed at Chapter creation step")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_create_chapters",
                        category="artifacts",
                        status="fail",
                        message=f"Chapter creation failed: {e}",
                        details={"error": str(e)}
                    )
                )

        # 3. Run mock chapter generation
        if book_id and request.run_mock_chapter_generation:
            try:
                if not chapter_ids:
                    chapters = self.db.query(Chapter).filter_by(book_id=book_id).order_by(Chapter.chapter_number).all()
                    chapter_ids = [ch.id for ch in chapters]

                if chapter_ids:
                    gen_req = ChapterGenerationRequest(
                        book_id=book_id,
                        chapter_ids=chapter_ids,
                        workflow_name="full_agent_pipeline",
                        execution_mode="mock",
                        traced=True,
                        persist_traces=True,
                        build_context_pack=False,
                        persist_chapter_content=True,
                        overwrite_existing=True,
                        max_chapters=request.max_chapters,
                        metadata=request.metadata,
                    )
                    gen_resp = self.chapter_generation_service.generate_chapters(gen_req)
                    run_id = gen_resp.run_id
                    generated_chapter_count = gen_resp.completed_count
                    
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name="dry_run_generate_chapters",
                            category="workflows",
                            status="pass" if generated_chapter_count > 0 else "warning",
                            message=f"Mock chapter generation completed: {generated_chapter_count} chapter(s) generated.",
                            details={"run_id": str(run_id), "completed_count": generated_chapter_count}
                        )
                    )
                else:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name="dry_run_generate_chapters",
                            category="workflows",
                            status="warning",
                            message="Skipped chapter generation: no chapters found.",
                            details={}
                        )
                    )
            except Exception as e:
                logger.exception("Dry run failed at Chapter generation step")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_generate_chapters",
                        category="workflows",
                        status="fail",
                        message=f"Mock chapter generation failed: {e}",
                        details={"error": str(e)}
                    )
                )

        # 4. Run mock memory extraction
        if book_id and request.run_memory_extraction:
            try:
                target_chapters = self.db.query(Chapter).filter_by(book_id=book_id).order_by(Chapter.chapter_number).all()
                if target_chapters:
                    extracted_count = 0
                    for ch in target_chapters[:request.max_chapters]:
                        mem_req = MemoryExtractionRequest(
                            book_id=book_id,
                            run_id=run_id,
                            chapter_id=ch.id,
                            source_type="chapter",
                            execution_mode="mock",
                            persist_memory=True,
                            overwrite_existing=True,
                            metadata=request.metadata,
                        )
                        mem_resp = self.memory_extraction_service.extract_memory(mem_req)
                        extracted_count += mem_resp.written_count
                    memory_written_count = extracted_count
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name="dry_run_extract_memory",
                            category="artifacts",
                            status="pass" if memory_written_count > 0 else "warning",
                            message=f"Mock memory extraction completed: {memory_written_count} record(s) written.",
                            details={"written_count": memory_written_count}
                        )
                    )
                else:
                    checks.append(
                        BackendReadinessCheckItem(
                            check_name="dry_run_extract_memory",
                            category="artifacts",
                            status="warning",
                            message="Skipped memory extraction: no chapters found.",
                            details={}
                        )
                    )
            except Exception as e:
                logger.exception("Dry run failed at Memory extraction step")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_extract_memory",
                        category="artifacts",
                        status="fail",
                        message=f"Mock memory extraction failed: {e}",
                        details={"error": str(e)}
                    )
                )

        # 5. Run DOCX export generation
        if book_id and request.run_export_generation:
            try:
                export_req = BookExportRequest(
                    book_id=book_id,
                    run_id=run_id,
                    export_types=["docx"],
                    include_front_matter=True,
                    include_back_matter=True,
                    include_toc=True,
                    include_glossary=True,
                    include_bibliography=True,
                    overwrite_existing=True,
                    prefer_final_text=True,
                    metadata=request.metadata,
                )
                export_resp = self.document_export_service.export_book(export_req)
                export_file_count = sum(1 for f in export_resp.files if f.status == "ready")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_export_generation",
                        category="artifacts",
                        status="pass" if export_file_count > 0 else "warning",
                        message=f"DOCX export generated: {export_file_count} file(s) created.",
                        details={"files": [str(f.file_name) for f in export_resp.files]}
                    )
                )
            except Exception as e:
                logger.exception("Dry run failed at export generation step")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_export_generation",
                        category="artifacts",
                        status="fail",
                        message=f"DOCX export generation failed: {e}",
                        details={"error": str(e)}
                    )
                )

        # 6. Run delivery bundle generation
        if book_id and request.run_delivery_bundle:
            try:
                bundle_req = DeliveryBundleRequest(
                    book_id=book_id,
                    run_id=run_id,
                    include_eval_report=True,
                    include_prompt_dossier=True,
                    include_architecture_summary=True,
                    include_memory_report=True,
                    include_trace_summary=True,
                    include_export_summary=True,
                    write_files=True,
                    metadata=request.metadata,
                )
                bundle_resp = self.delivery_bundle_service.generate_delivery_bundle(bundle_req)
                delivery_artifact_count = sum(1 for a in bundle_resp.artifacts if a.status == "ready")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_delivery_bundle",
                        category="artifacts",
                        status="pass" if delivery_artifact_count > 0 else "warning",
                        message=f"Delivery bundle generated: {delivery_artifact_count} artifact(s) created.",
                        details={"manifest": bundle_resp.manifest}
                    )
                )
            except Exception as e:
                logger.exception("Dry run failed at delivery bundle generation step")
                checks.append(
                    BackendReadinessCheckItem(
                        check_name="dry_run_delivery_bundle",
                        category="artifacts",
                        status="fail",
                        message=f"Delivery bundle generation failed: {e}",
                        details={"error": str(e)}
                    )
                )

        # Evaluate final status
        overall_status = "pass"
        if any(c.status == "fail" for c in checks):
            overall_status = "fail"
        elif any(c.status == "warning" for c in checks):
            overall_status = "warning"

        return EndToEndDryRunResponse(
            status=overall_status,
            book_id=book_id,
            run_id=run_id,
            chapter_ids=chapter_ids,
            generated_chapter_count=generated_chapter_count,
            memory_written_count=memory_written_count,
            export_file_count=export_file_count,
            delivery_artifact_count=delivery_artifact_count,
            checks=checks,
            metadata=request.metadata,
        )
