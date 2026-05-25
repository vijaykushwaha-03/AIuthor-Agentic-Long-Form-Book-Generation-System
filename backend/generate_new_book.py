import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("generate_new_book")

# Add app to python path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.models import BookProject, Chapter
from app.schemas.book import BookProjectCreate
from app.schemas.chapter import ChapterCreate
from app.schemas.enums import TonePreset
from app.services.book_service import BookProjectService
from app.services.chapter_service import ChapterService
from app.services.chapter_generation_service import ChapterGenerationService
from app.services.document_export_service import DocumentExportService
from app.services.delivery_bundle_service import DeliveryBundleService
from app.workflows.schemas import (
    ChapterGenerationRequest,
    BookExportRequest,
    DeliveryBundleRequest
)

def main():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    logger.info("Initializing services...")
    book_svc = BookProjectService(db)
    chapter_svc = ChapterService(db)
    gen_svc = ChapterGenerationService(db)
    export_svc = DocumentExportService(db)
    bundle_svc = DeliveryBundleService(db)

    # 1. Create a new Book Project
    logger.info("Creating a new book project...")
    book_payload = BookProjectCreate(
        topic="Architecting Modern Retrieval-Augmented Generation Systems",
        reader_profile="AI Engineers, Software Architects, and LLM practitioners looking to build robust production-grade RAG applications.",
        genre="Technology & Software Engineering",
        tone=TonePreset.CONVERSATIONAL,
        target_chapters=3,
        words_per_chapter=600,
        project_metadata={
            "title": "Architecting Modern Retrieval-Augmented Generation Systems",
            "subtitle": "A Practical Guide to Vector Search, Hybrid Retrieval, and Evaluation",
            "author": "Vijay Patel"
        }
    )
    book = book_svc.create_book_project(book_payload)
    logger.info(f"Book created with ID: {book.id}")

    # 2. Create the 3 Chapters
    chapters_data = [
        {
            "chapter_number": 1,
            "title": "The Foundations of RAG",
            "summary": "An introduction to Retrieval-Augmented Generation, why it is needed to mitigate hallucinations and extend LLM knowledge limits, and the high-level architecture of RAG."
        },
        {
            "chapter_number": 2,
            "title": "Hybrid Retrieval and Vector Search",
            "summary": "A deep dive into dense vector databases, semantic embeddings, keyword-based BM25 search, and how to combine lexical and semantic retrieval with reciprocal rank fusion (RRF) and re-ranking."
        },
        {
            "chapter_number": 3,
            "title": "Evaluation, Observability, and Production Guardrails",
            "summary": "How to measure RAG quality using metrics like faithfulness, answer relevance, and context recall, tracing LLM calls, and setting up guardrails."
        }
    ]

    chapters = []
    for ch_data in chapters_data:
        logger.info(f"Creating Chapter {ch_data['chapter_number']}: {ch_data['title']}...")
        payload = ChapterCreate(
            book_id=book.id,
            chapter_number=ch_data["chapter_number"],
            title=ch_data["title"],
            summary=ch_data["summary"],
            tone=TonePreset.CONVERSATIONAL,
            status="planned",
            chapter_contract={
                "chapter_number": ch_data["chapter_number"],
                "title": ch_data["title"],
                "purpose": ch_data["summary"],
                "key_concepts": [],
                "required_facts": [],
                "callback_opportunities": []
            }
        )
        ch = chapter_svc.create_chapter(book.id, payload)
        chapters.append(ch)

    # 3. Generate Chapters Sequentially
    logger.info("Starting chapter generation loop (real_dev mode)...")
    
    # We will run real_dev mode
    gen_req = ChapterGenerationRequest(
        book_id=book.id,
        run_id=None, # Automatically created by service
        execution_mode="real_dev",
        traced=True,
        persist_traces=True,
        build_context_pack=True, # Will fallback safely if no docs are loaded
        persist_chapter_content=True,
        overwrite_existing=True
    )
    
    gen_resp = gen_svc.generate_chapters(gen_req)
    run_id = gen_resp.run_id
    logger.info(f"Chapter generation complete. Run ID: {run_id}. Status: {gen_resp.status}")
    
    for ch_res in gen_resp.chapters:
        logger.info(f"  - Chapter {ch_res.chapter_number}: status={ch_res.status}, workflow_status={ch_res.workflow_status}, size={ch_res.content_chars} chars")
        if ch_res.error_message:
            logger.error(f"    Error: {ch_res.error_message}")

    # 4. Export Book
    logger.info("Exporting book...")
    export_req = BookExportRequest(
        book_id=book.id,
        run_id=run_id,
        export_types=["docx"], # docx is mandatory
        include_front_matter=True,
        include_back_matter=True,
        include_toc=True,
        include_glossary=True,
        include_bibliography=True,
        prefer_final_text=True
    )
    export_resp = export_svc.export_book(export_req)
    logger.info(f"Book export complete. Status: {export_resp.status}")
    for f in export_resp.files:
        logger.info(f"  - Exported {f.export_type} file: {f.file_name} at {f.file_path}")

    # 5. Package Deliverables
    logger.info("Packaging deliverables bundle...")
    bundle_req = DeliveryBundleRequest(
        book_id=book.id,
        run_id=run_id,
        include_eval_report=True,
        include_prompt_dossier=True,
        include_architecture_summary=True,
        include_memory_report=True,
        include_trace_summary=True,
        include_export_summary=True,
        write_files=True
    )
    bundle_resp = bundle_svc.generate_delivery_bundle(bundle_req)
    logger.info(f"Delivery bundle complete. Status: {bundle_resp.status}")

    print("\n==================================================")
    print("SUCCESSFULLY COMPLETED NEW BOOK PROJECT RUN!")
    print(f"Book ID: {book.id}")
    print(f"Run ID:  {run_id}")
    print("==================================================\n")

if __name__ == "__main__":
    main()
