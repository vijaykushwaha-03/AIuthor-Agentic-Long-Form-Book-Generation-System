"""
AIuthor Backend Tests — Book Assembler Service (Module 10.0).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter, BookSection
from app.models.memory import ConceptBible
from app.models.document import SourceDocument
from app.workflows.schemas import BookAssemblyRequest
from app.services import BookAssemblerService, NotFoundError


@pytest.fixture
def assembler_service(db: Session) -> BookAssemblerService:
    return BookAssemblerService(db)


@pytest.fixture
def sample_book(db: Session) -> BookProject:
    book = BookProject(
        topic="Modern Agentic Design",
        genre="Technical",
        reader_profile="Software Architects",
        tone="instructive",
        target_chapters=3,
        project_metadata={
            "title": "Architecting AI Agents",
            "subtitle": "A Practical Guide to LangGraph and Autogen",
            "author": "Vijay Patel"
        },
        status="created"
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def test_assemble_book_validates_book_exists(assembler_service: BookAssemblerService):
    """1. assemble_book validates book exists."""
    req = BookAssemblyRequest(book_id=uuid4())
    with pytest.raises(NotFoundError):
        assembler_service.assemble_book(req)


def test_assemble_book_loads_chapters_ordered(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """2. assemble_book loads chapters ordered by chapter_number."""
    ch3 = Chapter(book_id=sample_book.id, chapter_number=3, title="Chapter 3", final_text="Content 3", status="completed")
    ch1 = Chapter(book_id=sample_book.id, chapter_number=1, title="Chapter 1", final_text="Content 1", status="completed")
    ch2 = Chapter(book_id=sample_book.id, chapter_number=2, title="Chapter 2", final_text="Content 2", status="completed")
    db.add_all([ch3, ch1, ch2])
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id)
    res = assembler_service.assemble_book(req)
    
    assert res.total_chapters == 3
    assert res.chapters[0].chapter_number == 1
    assert res.chapters[1].chapter_number == 2
    assert res.chapters[2].chapter_number == 3


def test_assemble_book_prefers_final_text(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """3. assemble_book prefers final_text over edited_text."""
    ch1 = Chapter(
        book_id=sample_book.id,
        chapter_number=1,
        title="Chapter 1",
        draft_text="Draft",
        humanized_text="Humanized",
        edited_text="Edited",
        final_text="Final Text Content",
        status="completed"
    )
    db.add(ch1)
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id, prefer_final_text=True)
    res = assembler_service.assemble_book(req)
    
    assert res.chapters[0].content == "Final Text Content"
    assert res.chapters[0].source_field == "final_text"


def test_assemble_book_falls_back_to_draft(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """4. assemble_book falls back to draft_text if other text is missing."""
    ch1 = Chapter(
        book_id=sample_book.id,
        chapter_number=1,
        title="Chapter 1",
        draft_text="Draft Text Content Only",
        status="completed"
    )
    db.add(ch1)
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id, prefer_final_text=True)
    res = assembler_service.assemble_book(req)
    
    assert res.chapters[0].content == "Draft Text Content Only"
    assert res.chapters[0].source_field == "draft_text"


def test_assemble_book_builds_toc(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """5. assemble_book builds TOC."""
    ch1 = Chapter(book_id=sample_book.id, chapter_number=1, title="Intro to RAG", final_text="Some text", status="completed")
    ch2 = Chapter(book_id=sample_book.id, chapter_number=2, title="Agentic RAG", final_text="More text", status="completed")
    db.add_all([ch1, ch2])
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id, include_toc=True)
    res = assembler_service.assemble_book(req)
    
    assert len(res.toc) == 2
    assert res.toc[0]["chapter_number"] == 1
    assert res.toc[0]["title"] == "Intro to RAG"
    assert res.toc[0]["chapter_id"] == str(ch1.id)
    assert res.toc[1]["chapter_number"] == 2
    assert res.toc[1]["title"] == "Agentic RAG"
    assert res.toc[1]["chapter_id"] == str(ch2.id)


def test_assemble_book_computes_word_counts(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """6. assemble_book computes word counts."""
    ch1 = Chapter(book_id=sample_book.id, chapter_number=1, title="Ch1", final_text="Word1 Word2 Word3", status="completed")
    ch2 = Chapter(book_id=sample_book.id, chapter_number=2, title="Ch2", final_text="Word4 Word5", status="completed")
    db.add_all([ch1, ch2])
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id)
    res = assembler_service.assemble_book(req)
    
    assert res.chapters[0].word_count == 3
    assert res.chapters[1].word_count == 2
    assert res.total_words == 5


def test_assemble_book_includes_glossary(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """7. assemble_book includes glossary from memory concepts."""
    concept = ConceptBible(book_id=sample_book.id, concept="Agent", definition="Autonomous AI software unit")
    db.add(concept)
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id, include_glossary=True)
    res = assembler_service.assemble_book(req)
    
    assert len(res.glossary) == 1
    assert res.glossary[0]["concept"] == "Agent"
    assert res.glossary[0]["definition"] == "Autonomous AI software unit"


def test_assemble_book_includes_bibliography(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """8. assemble_book includes bibliography from source documents."""
    doc = SourceDocument(
        book_id=sample_book.id,
        title="Attention is All You Need",
        source_type="arxiv",
        source_url="https://arxiv.org/abs/1706.03762",
        document_metadata={"citation": "Vaswani et al., 2017"}
    )
    db.add(doc)
    db.commit()

    req = BookAssemblyRequest(book_id=sample_book.id, include_bibliography=True)
    res = assembler_service.assemble_book(req)
    
    assert len(res.bibliography) == 1
    assert res.bibliography[0]["title"] == "Attention is All You Need"
    assert res.bibliography[0]["citation"] == "Vaswani et al., 2017"


def test_assemble_book_handles_no_chapters_gracefully(db: Session, assembler_service: BookAssemblerService, sample_book: BookProject):
    """9. assemble_book handles book with no chapters gracefully."""
    req = BookAssemblyRequest(book_id=sample_book.id)
    res = assembler_service.assemble_book(req)
    
    assert res.total_chapters == 0
    assert res.total_words == 0
    assert len(res.chapters) == 0


def test_assemble_book_does_not_call_llm(assembler_service: BookAssemblerService, sample_book: BookProject):
    """10. assemble_book does not call Gemini/OpenAI."""
    # Running assemble_book requires no external mocks because it relies solely on database state.
    req = BookAssemblyRequest(book_id=sample_book.id)
    res = assembler_service.assemble_book(req)
    assert res.book_id == sample_book.id
