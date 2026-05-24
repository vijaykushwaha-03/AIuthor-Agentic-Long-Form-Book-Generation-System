#!/usr/bin/env python
"""
AIuthor Backend — Live End-to-End Book Generation for LLM Agents.
Creates a book project, plans 3 chapters, runs real Gemini workflows sequentially for all 3 chapters,
performs incremental memory extraction, exports the book to DOCX,
evaluates the project, and packages the delivery bundle.
"""
from __future__ import annotations

import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import app.main FIRST to establish correct module loading sequence and prevent circular imports
import app.main

import uuid
import logging
from datetime import datetime, timezone

# Enable real LLM workflow and memory APIs
os.environ["ENABLE_REAL_WORKFLOW_TEST_API"] = "true"
os.environ["ENABLE_REAL_MEMORY_TEST_API"] = "true"
os.environ["ENABLE_REAL_AGENT_TEST_API"] = "true"

from app.database import get_session_local, ping_db
from app.schemas.book import BookProjectCreate
from app.schemas.chapter import ChapterCreate, ChapterContract
from app.schemas.enums import TonePreset, ChapterStatus
from app.workflows.schemas import (
    ChapterGenerationRequest,
    MemoryExtractionRequest,
    BookExportRequest,
    EvaluationReportRequest,
    DeliveryBundleRequest,
)

from app.services.book_service import BookProjectService
from app.services.chapter_service import ChapterService
from app.services.chapter_generation_service import ChapterGenerationService
from app.services.memory_extraction_service import MemoryExtractionService
from app.services.document_export_service import DocumentExportService
from app.services.evaluation_report_service import EvaluationReportService
from app.services.delivery_bundle_service import DeliveryBundleService

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("live_agents_runner")

def main():
    logger.info("Verifying PostgreSQL database connection...")
    try:
        ping_db()
        logger.info("Database connection: OK")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # 1. Create Book Project
        logger.info("\n=== STEP 1: Creating Book Project ===")
        book_service = BookProjectService(db)
        
        book_create_payload = BookProjectCreate(
            topic="LLM Agents",
            reader_profile="Software engineers, architects, and AI practitioners building production-grade agent systems.",
            genre="Technical Nonfiction",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=3,
            words_per_chapter=2000,
            project_metadata={
                "title": "Production LLM Agents: Architecture, Memory, and Tools",
                "author": "Vijay Patel",
                "assessment_scenario": "LLM Agents Production Run",
                "run_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        book = book_service.create_book_project(book_create_payload)
        book_id = book.id
        logger.info(f"Book Project created successfully. ID: {book_id}")

        # 2. Create Planned Chapters
        logger.info("\n=== STEP 2: Creating Planned Chapters ===")
        chapter_service = ChapterService(db)

        # Chapter 1
        ch1_payload = ChapterCreate(
            book_id=book_id,
            chapter_number=1,
            title="Introduction to Agentic Workflows",
            summary="Fundamentals of autonomous agentic loops, prompt routing, and tool integration.",
            chapter_contract=ChapterContract(
                chapter_number=1,
                title="Introduction to Agentic Workflows",
                purpose="Explain loops, reasoning patterns, and tool execution.",
                key_concepts=["Agentic Loop", "Tool Calling", "Prompt Routing"],
                required_facts=["LLM agents execute actions iteratively in a sense-think-act loop."],
                callback_opportunities=[]
            ),
            tone=TonePreset.CONVERSATIONAL,
            status=ChapterStatus.PLANNED
        )
        ch1 = chapter_service.create_chapter(book_id, ch1_payload)
        logger.info(f"Chapter 1 planned. ID: {ch1.id}")

        # Chapter 2
        ch2_payload = ChapterCreate(
            book_id=book_id,
            chapter_number=2,
            title="Agentic Memory and State Management",
            summary="Designing short-term context storage, long-term vector-search memory, and database state.",
            chapter_contract=ChapterContract(
                chapter_number=2,
                title="Agentic Memory and State Management",
                purpose="Explain how short-term context and long-term memory retrieval work.",
                key_concepts=["Short-term Memory", "Semantic Vector Memory", "State Persistence"],
                required_facts=["Vector retrieval provides external context without retraining models."],
                callback_opportunities=["Introduction to Agentic Workflows"]
            ),
            tone=TonePreset.CONVERSATIONAL,
            status=ChapterStatus.PLANNED
        )
        ch2 = chapter_service.create_chapter(book_id, ch2_payload)
        logger.info(f"Chapter 2 planned. ID: {ch2.id}")

        # Chapter 3
        ch3_payload = ChapterCreate(
            book_id=book_id,
            chapter_number=3,
            title="Multi-Agent Orchestration and Collaboration",
            summary="Patterns of multi-agent coordination, routing control flow, and state sharing.",
            chapter_contract=ChapterContract(
                chapter_number=3,
                title="Multi-Agent Orchestration and Collaboration",
                purpose="Detail multi-agent patterns and LangGraph routers.",
                key_concepts=["Multi-Agent Graph", "Routing Node", "Shared State Schema"],
                required_facts=["StateGraph allows complex cyclic orchestrations of multiple agents."],
                callback_opportunities=["Introduction to Agentic Workflows", "Agentic Memory and State Management"]
            ),
            tone=TonePreset.CONVERSATIONAL,
            status=ChapterStatus.PLANNED
        )
        ch3 = chapter_service.create_chapter(book_id, ch3_payload)
        logger.info(f"Chapter 3 planned. ID: {ch3.id}")

        # 3. Generate Chapters & Extract Memory sequentially
        logger.info("\n=== STEP 3: Generating Chapters and Extracting Memory ===")
        gen_service = ChapterGenerationService(db)
        memory_service = MemoryExtractionService(db)
        
        run_id = None
        for ch in [ch1, ch2, ch3]:
            logger.info(f"\n--- Generating Chapter {ch.chapter_number}: {ch.title} ---")
            gen_request = ChapterGenerationRequest(
                book_id=book_id,
                chapter_ids=[ch.id],
                workflow_name="full_agent_pipeline",
                execution_mode="real_dev",
                traced=True,
                persist_traces=True,
                build_context_pack=False,
                persist_chapter_content=True,
                overwrite_existing=True,
                max_chapters=3,
                metadata={"run_type": "live_e2e_agents"}
            )
            
            gen_response = gen_service.generate_chapters(gen_request)
            run_id = gen_response.run_id
            logger.info(f"Chapter {ch.chapter_number} generation finished. Status: {gen_response.status}")
            
            db.refresh(ch)
            logger.info(f"Chapter {ch.chapter_number} word count: {ch.word_count}")
            
            # Extract memory
            logger.info(f"Extracting Continuity Memory from Chapter {ch.chapter_number}...")
            mem_request = MemoryExtractionRequest(
                book_id=book_id,
                run_id=run_id,
                chapter_id=ch.id,
                source_type="chapter",
                execution_mode="real_dev",
                persist_memory=True,
                overwrite_existing=True,
                include_facts=True,
                include_concepts=True,
                include_characters=True,
                include_callbacks=True,
                include_tone=True,
                include_decisions=True
            )
            mem_response = memory_service.extract_memory(mem_request)
            logger.info(f"Memory extraction finished. Status: {mem_response.status}")
            logger.info(f"Total candidates: {mem_response.total_candidates}, Written to DB: {mem_response.written_count}")

        # 4. Export DOCX/PDF
        logger.info("\n=== STEP 4: Exporting Manuscript (DOCX + PDF) ===")
        export_service = DocumentExportService(db)
        
        export_request = BookExportRequest(
            book_id=book_id,
            run_id=run_id,
            export_types=["docx", "pdf"],
            include_front_matter=True,
            include_back_matter=True,
            include_toc=True,
            include_glossary=True,
            include_bibliography=True,
            include_memory_notes=True,
            prefer_final_text=True
        )
        
        export_response = export_service.export_book(export_request)
        logger.info(f"Export finished. Overall status: {export_response.status}")
        for file_item in export_response.files:
            logger.info(f"- Format: {file_item.export_type.upper()}")
            logger.info(f"  Status: {file_item.status}")
            if file_item.status == "ready":
                logger.info(f"  Path: {file_item.file_path}")
                logger.info(f"  Size: {file_item.file_size_bytes} bytes")
            else:
                logger.info(f"  Error: {file_item.error_message}")

        # 5. Generate Evaluation Report
        logger.info("\n=== STEP 5: Generating Quality Evaluation Report ===")
        eval_report_service = EvaluationReportService(db)
        
        eval_request = EvaluationReportRequest(
            book_id=book_id,
            run_id=run_id,
            include_chapter_checks=True,
            include_export_checks=True,
            include_trace_checks=True,
            include_memory_checks=True,
            persist_eval_results=True
        )
        
        eval_response = eval_report_service.generate_evaluation_report(eval_request)
        logger.info(f"Evaluation report generated. Status: {eval_response.status}")
        logger.info(f"Passed checks: {eval_response.pass_count}/{eval_response.total_checks}")

        # 6. Generate Delivery Bundle
        logger.info("\n=== STEP 6: Packaging and Serializing Delivery Bundle ===")
        delivery_service = DeliveryBundleService(db)
        
        delivery_request = DeliveryBundleRequest(
            book_id=book_id,
            run_id=run_id,
            include_eval_report=True,
            include_prompt_dossier=True,
            include_architecture_summary=True,
            include_memory_report=True,
            include_trace_summary=True,
            include_export_summary=True,
            write_files=True
        )
        
        delivery_response = delivery_service.generate_delivery_bundle(delivery_request)
        logger.info(f"Delivery bundle packaged. Overall status: {delivery_response.status}")
        logger.info(f"Manifest written to: {delivery_response.manifest.get('artifacts', [])[-1].get('file_path')}")
        logger.info("\nList of packaged artifacts:")
        for artifact in delivery_response.artifacts:
            logger.info(f"- Type: {artifact.artifact_type}")
            logger.info(f"  Status: {artifact.status}")
            if artifact.status == "ready":
                logger.info(f"  Path: {artifact.file_path}")
                logger.info(f"  Size: {artifact.file_size_bytes} bytes")
            else:
                logger.info(f"  Error: {artifact.error_message}")

        logger.info("\n🎉 E2E Live Book Generation and Export completed successfully! 🎉")

    except Exception as e:
        logger.exception(f"An error occurred during live E2E run: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
