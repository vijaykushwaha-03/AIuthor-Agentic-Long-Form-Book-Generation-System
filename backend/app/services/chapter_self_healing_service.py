"""
AIuthor Backend — Chapter Self-Healing Service (Module 8.2).
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.models import BookProject, BookRun, Chapter, BookSection, CallbackIndex, ConceptBible
from app.schemas.rag import ContextPackRequest
from app.schemas.chapter import ChapterInsertRequest
from app.schemas.enums import ChapterStatus
from app.workflows.exceptions import WorkflowExecutionError
from app.services.exceptions import NotFoundError, ValidationServiceError
from app.services.book_service import BookProjectService
from app.services.run_service import BookRunService
from app.services.chapter_service import ChapterService
from app.services.section_service import BookSectionService
from app.services.context_pack_service import ContextPackService
from app.services.workflow_execution_service import WorkflowExecutionService
from app.services.workflow_observability_service import WorkflowObservabilityService

from app.workflows.schemas import (
    InsertChapterRepairRequest,
    StructureRepairItem,
    InsertChapterRepairResponse,
    WorkflowInput,
    WorkflowTraceRequest,
)

logger = logging.getLogger(__name__)


class ChapterSelfHealingService:
    """
    Coordinates chapter insertions and self-healing book repair pipelines sequentially.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.book_service = BookProjectService(db)
        self.run_service = BookRunService(db)
        self.chapter_service = ChapterService(db)
        self.section_service = BookSectionService(db)
        self.context_pack_service = ContextPackService(db)
        self.workflow_service = WorkflowExecutionService(db)
        self.workflow_observability_service = WorkflowObservabilityService(db)

    def _get_book(self, book_id: UUID) -> BookProject:
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _get_or_create_run(self, book: BookProject, run_id: UUID | None = None) -> BookRun:
        if run_id is not None:
            run = self.db.get(BookRun, run_id)
            if run is None:
                raise NotFoundError(
                    message="Book run not found",
                    code="run_not_found",
                    details={"run_id": str(run_id)},
                )
            if run.book_id != book.id:
                raise ValidationServiceError(
                    message="Book run does not belong to the specified book project",
                    code="run_book_mismatch",
                )
            return run
        else:
            from app.schemas.run import BookRunCreate
            run_payload = BookRunCreate(
                book_id=book.id,
                run_metadata={
                    "workflow_name": "full_agent_pipeline",
                    "module": "8.2",
                    "mode": "insert_chapter_self_healing",
                    "created_automatically": True,
                },
            )
            return self.run_service.create_run(run_payload)

    def _insert_chapter(self, request: InsertChapterRepairRequest, book: BookProject) -> tuple[Chapter, list[Chapter]]:
        # existing ChapterService.insert_chapter(book_id, payload) inserts after "after_chapter"
        # n-th position insertion maps to after_chapter = n - 1
        after_chapter = request.insert_at_chapter_number - 1

        # Safely map book.tone to TonePreset enum; fall back to None if not a valid preset
        from app.schemas.enums import TonePreset
        try:
            safe_tone = TonePreset(book.tone) if book.tone else None
        except (ValueError, KeyError):
            safe_tone = None

        insert_payload = ChapterInsertRequest(
            after_chapter=after_chapter,
            title=request.title,
            purpose=request.summary or f"Inserted chapter: {request.title}",
            tone=safe_tone,
            metadata={
                "inserted_via_self_healing": True,
                "repair_required": True,
                "inserted_at": datetime.utcnow().isoformat(),
                "original_insert_position": request.insert_at_chapter_number,
                "summary": request.summary,
            }
        )

        inserted_chapter = self.chapter_service.insert_chapter(book.id, insert_payload)

        # Mark as drafting
        inserted_chapter.status = "drafting"
        self.db.commit()
        self.db.refresh(inserted_chapter)

        # Shift all chapters at or above this insertion point
        all_chapters = (
            self.db.query(Chapter)
            .filter(Chapter.book_id == book.id)
            .order_by(asc(Chapter.chapter_number))
            .all()
        )
        affected_chapters = [
            ch for ch in all_chapters 
            if ch.id != inserted_chapter.id and ch.chapter_number > request.insert_at_chapter_number
        ]

        return inserted_chapter, affected_chapters

    def _verify_chapter_numbering(self, book_id: UUID) -> list[StructureRepairItem]:
        chapters = (
            self.db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .order_by(asc(Chapter.chapter_number))
            .all()
        )

        repair_items = []
        numbers_before = [ch.chapter_number for ch in chapters]
        
        # Verify sequence 1..N
        is_continuous = True
        for idx, ch in enumerate(chapters, start=1):
            if ch.chapter_number != idx:
                is_continuous = False
                break
        
        if not is_continuous:
            # Reorder chapters
            reordered = self.chapter_service.reorder_chapters(book_id)
            numbers_after = [ch.chapter_number for ch in reordered]
            
            repair_items.append(
                StructureRepairItem(
                    item_type="numbering",
                    status="success",
                    message="Chapter numbering was discontinuous or duplicated. Successfully reordered sequentially.",
                    before_value={"chapter_numbers": numbers_before},
                    after_value={"chapter_numbers": numbers_after},
                    metadata={"total_chapters": len(reordered)},
                )
            )
        else:
            repair_items.append(
                StructureRepairItem(
                    item_type="numbering",
                    status="success",
                    message="Chapter sequence verified to be continuous and sequentially correct.",
                    before_value={"chapter_numbers": numbers_before},
                    after_value={"chapter_numbers": numbers_before},
                    metadata={"total_chapters": len(chapters)},
                )
            )
            
        return repair_items

    def _repair_toc(self, book: BookProject, inserted_chapter: Chapter, affected_chapters: list[Chapter]) -> list[StructureRepairItem]:
        toc_section = (
            self.db.query(BookSection)
            .filter(BookSection.book_id == book.id, BookSection.section_type == "toc")
            .first()
        )
        
        repair_items = []
        if toc_section:
            before_content = toc_section.content or ""
            
            # Rebuild TOC
            all_chapters = (
                self.db.query(Chapter)
                .filter(Chapter.book_id == book.id)
                .order_by(asc(Chapter.chapter_number))
                .all()
            )
            toc_lines = ["# Table of Contents\n"]
            for ch in all_chapters:
                toc_lines.append(f"{ch.chapter_number}. {ch.title}")
            after_content = "\n".join(toc_lines)
            
            toc_section.content = after_content
            toc_section.status = "completed"
            
            meta = dict(toc_section.section_metadata) if toc_section.section_metadata else {}
            meta.update({
                "repaired_at": datetime.utcnow().isoformat(),
                "inserted_chapter_id": str(inserted_chapter.id),
                "affected_chapters_shifted": [ch.chapter_number for ch in affected_chapters]
            })
            toc_section.section_metadata = meta
            
            self.db.commit()
            self.db.refresh(toc_section)
            
            repair_items.append(
                StructureRepairItem(
                    item_type="toc",
                    item_id=toc_section.id,
                    status="success",
                    message="Table of Contents section was successfully updated with the shifted chapter structure.",
                    before_value=before_content,
                    after_value=after_content,
                    metadata={"affected_chapters_count": len(affected_chapters)},
                )
            )
        else:
            repair_items.append(
                StructureRepairItem(
                    item_type="toc",
                    status="skipped",
                    message="No Table of Contents section found in the book. Skipped self-healing TOC content update.",
                )
            )
            
        return repair_items

    def _repair_callbacks(self, book: BookProject, inserted_chapter: Chapter, affected_chapters: list[Chapter]) -> list[StructureRepairItem]:
        # Query callbacks
        callbacks = (
            self.db.query(CallbackIndex)
            .filter(CallbackIndex.book_id == book.id)
            .all()
        )
        
        repair_items = []
        shifted_count = 0
        
        insert_pos = inserted_chapter.chapter_number
        
        for cb in callbacks:
            shifted = False
            before_source = cb.source_chapter
            before_target = cb.target_chapter
            
            if cb.source_chapter is not None and cb.source_chapter >= insert_pos:
                cb.source_chapter += 1
                shifted = True
            if cb.target_chapter is not None and cb.target_chapter >= insert_pos:
                cb.target_chapter += 1
                shifted = True
                
            if shifted:
                shifted_count += 1
                self.db.flush()
                repair_items.append(
                    StructureRepairItem(
                        item_type="callback",
                        item_id=cb.id,
                        status="success",
                        message=f"Shifted callback source/target chapter numbers referencing position >= {insert_pos}.",
                        before_value={"source": before_source, "target": before_target},
                        after_value={"source": cb.source_chapter, "target": cb.target_chapter},
                        metadata={"callback_id": str(cb.id)},
                    )
                )
                
        if shifted_count > 0:
            self.db.commit()
            
        # Store callback repair notes in inserted chapter chapter_contract
        contract = dict(inserted_chapter.chapter_contract) if inserted_chapter.chapter_contract else {}
        contract["callback_repair"] = {
            "repaired_at": datetime.utcnow().isoformat(),
            "shifted_callbacks_count": shifted_count,
        }
        inserted_chapter.chapter_contract = contract
        self.db.commit()
        
        if shifted_count == 0:
            repair_items.append(
                StructureRepairItem(
                    item_type="callback",
                    status="success",
                    message="No active callbacks required index renumbering offsets. Continuity verified.",
                )
            )
            
        return repair_items

    def _repair_glossary(self, book: BookProject, inserted_chapter: Chapter, affected_chapters: list[Chapter]) -> list[StructureRepairItem]:
        concepts = (
            self.db.query(ConceptBible)
            .filter(ConceptBible.book_id == book.id)
            .all()
        )
        
        repair_items = []
        shifted_concepts_count = 0
        insert_pos = inserted_chapter.chapter_number
        
        for cp in concepts:
            changed = False
            before_first = cp.first_chapter
            before_appears = list(cp.appears_in_chapters) if cp.appears_in_chapters else []
            
            if cp.first_chapter is not None and cp.first_chapter >= insert_pos:
                cp.first_chapter += 1
                changed = True
                
            if cp.appears_in_chapters:
                new_appears = []
                for ch_num in cp.appears_in_chapters:
                    if ch_num >= insert_pos:
                        new_appears.append(ch_num + 1)
                    else:
                        new_appears.append(ch_num)
                if new_appears != cp.appears_in_chapters:
                    cp.appears_in_chapters = new_appears
                    changed = True
                    
            if changed:
                shifted_concepts_count += 1
                self.db.flush()
                repair_items.append(
                    StructureRepairItem(
                        item_type="glossary",
                        item_id=cp.id,
                        status="success",
                        message=f"Adjusted first_chapter and appears_in_chapters list sequence for concept '{cp.concept}'.",
                        before_value={"first_chapter": before_first, "appears_in_chapters": before_appears},
                        after_value={"first_chapter": cp.first_chapter, "appears_in_chapters": cp.appears_in_chapters},
                        metadata={"concept": cp.concept},
                    )
                )
                
        if shifted_concepts_count > 0:
            self.db.commit()
            
        if shifted_concepts_count == 0:
            repair_items.append(
                StructureRepairItem(
                    item_type="glossary",
                    status="success",
                    message="No glossary concepts were impacted by the inserted chapter position.",
                )
            )
            
        return repair_items

    def _repair_back_matter(self, book: BookProject, inserted_chapter: Chapter, affected_chapters: list[Chapter]) -> list[StructureRepairItem]:
        back_sections = (
            self.db.query(BookSection)
            .filter(
                BookSection.book_id == book.id,
                BookSection.section_type.in_(["glossary", "references", "appendix", "index"])
            )
            .all()
        )
        
        repair_items = []
        for sec in back_sections:
            before_meta = dict(sec.section_metadata) if sec.section_metadata else {}
            after_meta = dict(before_meta)
            after_meta.update({
                "glossary_repaired_at": datetime.utcnow().isoformat(),
                "inserted_chapter_id": str(inserted_chapter.id),
                "affected_chapter_numbers": [ch.chapter_number for ch in affected_chapters]
            })
            sec.section_metadata = after_meta
            self.db.commit()
            self.db.refresh(sec)
            
            repair_items.append(
                StructureRepairItem(
                    item_type="back_matter",
                    item_id=sec.id,
                    status="success",
                    message=f"Updated back matter section metadata audit log for '{sec.section_type}'.",
                    before_value=before_meta,
                    after_value=after_meta,
                    metadata={"section_type": sec.section_type},
                )
            )
            
        if not back_sections:
            repair_items.append(
                StructureRepairItem(
                    item_type="back_matter",
                    status="skipped",
                    message="No glossary or back matter sections found in BookSection table. Skipped metadata repairs.",
                )
            )
            
        return repair_items

    def _build_repair_context_pack(
        self,
        request: InsertChapterRepairRequest,
        book: BookProject,
        inserted_chapter: Chapter,
    ) -> dict | None:
        if not request.build_context_pack:
            return None

        query = request.context_query
        if not query or not query.strip():
            query = f"{book.topic} inserted chapter {inserted_chapter.chapter_number}: {inserted_chapter.title} callbacks glossary continuity"

        context_req = ContextPackRequest(
            query=query,
            book_id=book.id,
            chapter_id=inserted_chapter.id,
            max_chunks=request.max_context_chunks,
            max_context_chars=request.max_context_chars,
            include_sources=True,
            include_memory_hints=False,
        )

        try:
            context_resp = self.context_pack_service.build_context_pack(context_req)
            import json
            context_dict = json.loads(context_resp.model_dump_json())
            if context_resp.total_chunks == 0:
                if "metadata" not in context_dict or context_dict["metadata"] is None:
                    context_dict["metadata"] = {}
                context_dict["metadata"]["note"] = "No context chunks found. Repair generated without RAG context."
            return context_dict
        except Exception as exc:
            logger.warning("Repair context pack skipped: %s", exc)
            return {
                "query": query,
                "book_id": str(book.id),
                "chapter_id": str(inserted_chapter.id),
                "context_text": "",
                "chunks": [],
                "citations": [],
                "total_chunks": 0,
                "total_context_chars": 0,
                "retrieval_mode": "hybrid_context_pack",
                "metadata": {
                    "note": "No context chunks found. Repair generated without RAG context.",
                    "error": str(exc),
                },
            }

    def _generate_inserted_chapter_content(
        self,
        request: InsertChapterRepairRequest,
        book: BookProject,
        run: BookRun,
        inserted_chapter: Chapter,
        affected_chapters: list[Chapter],
        context_pack: dict | None,
    ) -> tuple[str | None, dict | None]:
        if not request.generate_content:
            return None, None

        payload = dict(request.payload) if request.payload else {}
        payload.update({
            "book_topic": book.topic,
            "book_genre": book.genre,
            "book_reader_profile": book.reader_profile,
            "book_tone": book.tone,
            "run_id": str(run.id),
            "chapter_id": str(inserted_chapter.id),
            "chapter_number": inserted_chapter.chapter_number,
            "chapter_title": inserted_chapter.title,
            "chapter_summary": inserted_chapter.summary,
            "repair_intent": "chapter_insertion",
            "affected_chapters": [ch.chapter_number for ch in affected_chapters],
        })

        metadata = dict(request.metadata) if request.metadata else {}
        metadata.update({
            "module": "8.2",
            "generation_scope": "inserted_chapter_repair",
            "overwrite_existing": request.overwrite_existing_repair,
            "execution_mode": request.execution_mode,
            "workflow_name": request.workflow_name,
            "book_id": str(book.id),
            "run_id": str(run.id),
            "chapter_id": str(inserted_chapter.id),
            "traced": request.traced,
        })

        if request.traced:
            workflow_input = WorkflowTraceRequest(
                workflow_name=request.workflow_name,
                run_id=run.id,
                book_id=book.id,
                chapter_id=inserted_chapter.id,
                topic=book.topic,
                genre=book.genre,
                reader_profile=book.reader_profile,
                tone=book.tone,
                context_pack=context_pack,
                payload=payload,
                metadata=metadata,
                persist_traces=request.persist_traces,
            )
        else:
            workflow_input = WorkflowInput(
                workflow_name=request.workflow_name,
                run_id=run.id,
                book_id=book.id,
                chapter_id=inserted_chapter.id,
                topic=book.topic,
                genre=book.genre,
                reader_profile=book.reader_profile,
                tone=book.tone,
                context_pack=context_pack,
                payload=payload,
                metadata=metadata,
            )

        output = None
        trace_bundle = None

        if request.execution_mode == "mock":
            if request.traced:
                trace_resp = self.workflow_service.run_workflow_mock_traced(workflow_input)
                output = {
                    "final_content": trace_resp.final_content,
                    "steps": [s.model_dump() for s in trace_resp.steps],
                    "status": trace_resp.status,
                    "error_message": trace_resp.error_message,
                }
                trace_bundle = trace_resp.trace_bundle
            else:
                w_output = self.workflow_service.run_workflow_mock(workflow_input)
                output = {
                    "final_content": w_output.final_content,
                    "steps": [s.model_dump() for s in w_output.steps],
                    "status": w_output.status,
                    "error_message": w_output.error_message,
                }
        elif request.execution_mode == "real_dev":
            if request.traced:
                trace_resp = self.workflow_service.run_workflow_real_dev_traced(workflow_input)
                output = {
                    "final_content": trace_resp.final_content,
                    "steps": [s.model_dump() for s in trace_resp.steps],
                    "status": trace_resp.status,
                    "error_message": trace_resp.error_message,
                }
                trace_bundle = trace_resp.trace_bundle
            else:
                w_output = self.workflow_service.run_workflow_real_dev(workflow_input)
                output = {
                    "final_content": w_output.final_content,
                    "steps": [s.model_dump() for s in w_output.steps],
                    "status": w_output.status,
                    "error_message": w_output.error_message,
                }
        else:
            raise ValidationServiceError(
                message=f"Unsupported execution_mode '{request.execution_mode}'",
                code="invalid_execution_mode",
            )

        if output.get("status") == "failed":
            raise WorkflowExecutionError(
                message=output.get("error_message") or "Workflow node failed in content repair.",
                workflow_name=request.workflow_name,
            )

        # Extract step outputs safely
        writer_text = None
        humanizer_text = None
        edited_text = None
        final_text = output.get("final_content")

        steps = output.get("steps", [])
        for step in steps:
            agent = step.get("agent_name")
            cnt = step.get("content")
            if cnt:
                if agent == "writer":
                    writer_text = cnt
                elif agent == "humanizer":
                    humanizer_text = cnt
                elif agent == "editor":
                    edited_text = cnt

        if not final_text:
            final_text = edited_text or humanizer_text or writer_text

        if not final_text:
            raise ValidationServiceError(
                message="No content was generated by repair execution.",
                code="no_repair_content_generated",
            )

        # Persist into chapter fields
        inserted_chapter.draft_text = writer_text
        inserted_chapter.humanized_text = humanizer_text
        inserted_chapter.edited_text = edited_text
        inserted_chapter.final_text = final_text
        
        # Mark completed
        inserted_chapter.status = "completed"
        
        contract = dict(inserted_chapter.chapter_contract) if inserted_chapter.chapter_contract else {}
        contract.update({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "content_source": "full_agent_pipeline_repair",
            "traceable": request.traced,
            "repair_required": False,
        })
        inserted_chapter.chapter_contract = contract

        self.db.commit()
        self.db.refresh(inserted_chapter)

        preview = final_text[:1000] if final_text else None
        return preview, trace_bundle

    def repair_inserted_chapter(self, request: InsertChapterRepairRequest) -> InsertChapterRepairResponse:
        book = self._get_book(request.book_id)
        run = self._get_or_create_run(book, request.run_id)

        # Set run status to running
        run.status = "running"
        run.started_at = run.started_at or datetime.utcnow()
        self.db.commit()

        repair_items: list[StructureRepairItem] = []
        toc_repaired = False
        callbacks_repaired = False
        glossary_repaired = False
        back_matter_repaired = False
        affected_chapter_ids = []

        try:
            # 1. Insert Chapter
            inserted_chapter, affected_chapters = self._insert_chapter(request, book)
            affected_chapter_ids = [ch.id for ch in affected_chapters]

            # 2. Verify Sequence
            num_repairs = self._verify_chapter_numbering(book.id)
            repair_items.extend(num_repairs)

            # 3. Repair TOC
            if request.repair_toc:
                try:
                    toc_repairs = self._repair_toc(book, inserted_chapter, affected_chapters)
                    repair_items.extend(toc_repairs)
                    toc_repaired = any(r.status == "success" for r in toc_repairs)
                except Exception as e:
                    repair_items.append(
                        StructureRepairItem(
                            item_type="toc",
                            status="failed",
                            message=f"TOC repair partially failed: {e}",
                        )
                    )

            # 4. Repair Callbacks
            if request.repair_callbacks:
                try:
                    cb_repairs = self._repair_callbacks(book, inserted_chapter, affected_chapters)
                    repair_items.extend(cb_repairs)
                    callbacks_repaired = any(r.status == "success" for r in cb_repairs)
                except Exception as e:
                    repair_items.append(
                        StructureRepairItem(
                            item_type="callback",
                            status="failed",
                            message=f"Callbacks repair partially failed: {e}",
                        )
                    )

            # 5. Repair Glossary
            if request.repair_glossary:
                try:
                    gl_repairs = self._repair_glossary(book, inserted_chapter, affected_chapters)
                    repair_items.extend(gl_repairs)
                    glossary_repaired = any(r.status == "success" for r in gl_repairs)
                except Exception as e:
                    repair_items.append(
                        StructureRepairItem(
                            item_type="glossary",
                            status="failed",
                            message=f"Glossary repair partially failed: {e}",
                        )
                    )

            # 6. Repair Back Matter
            if request.repair_back_matter:
                try:
                    bm_repairs = self._repair_back_matter(book, inserted_chapter, affected_chapters)
                    repair_items.extend(bm_repairs)
                    back_matter_repaired = any(r.status == "success" for r in bm_repairs)
                except Exception as e:
                    repair_items.append(
                        StructureRepairItem(
                            item_type="back_matter",
                            status="failed",
                            message=f"Back matter repair partially failed: {e}",
                        )
                    )

            # 7. Context Pack
            context_pack = self._build_repair_context_pack(request, book, inserted_chapter)

            # 8. Run workflow content generation if requested
            preview = None
            trace_bundle = None
            if request.generate_content:
                preview, trace_bundle = self._generate_inserted_chapter_content(
                    request, book, run, inserted_chapter, affected_chapters, context_pack
                )

            # Mark affected chapters with repair audit tag
            for ch in affected_chapters:
                ch_contract = dict(ch.chapter_contract) if ch.chapter_contract else {}
                ch_contract.update({
                    "repair_checked_at": datetime.utcnow().isoformat() + "Z",
                    "chapter_number_shifted": True,
                })
                ch.chapter_contract = ch_contract
            self.db.commit()

            # Mark run completed
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            self.db.commit()

            return InsertChapterRepairResponse(
                book_id=book.id,
                run_id=run.id,
                inserted_chapter_id=inserted_chapter.id,
                inserted_chapter_number=inserted_chapter.chapter_number,
                workflow_name=request.workflow_name,
                execution_mode=request.execution_mode,
                status="completed",
                generated_content_preview=preview,
                repair_items=repair_items,
                affected_chapter_ids=affected_chapter_ids,
                toc_repaired=toc_repaired,
                callbacks_repaired=callbacks_repaired,
                glossary_repaired=glossary_repaired,
                back_matter_repaired=back_matter_repaired,
                trace_bundle=trace_bundle,
                metadata={
                    "total_repair_items": len(repair_items),
                    "context_pack_used": context_pack is not None,
                }
            )

        except Exception as exc:
            logger.error("Self-healing repair failed: %s", exc)
            
            # Rollback active db transaction
            self.db.rollback()

            # Update run to failed
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error_message = str(exc)
            self.db.commit()

            raise
