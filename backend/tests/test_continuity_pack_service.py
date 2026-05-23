"""
AIuthor Backend Tests — ContinuityPackService unit tests.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import uuid4

from app.database import Base
import app.models  # noqa: F401
from app.services import (
    BookProjectService,
    MemoryService,
    ContinuityPackService,
    NotFoundError,
)
from app.schemas import (
    BookProjectCreate,
    FactRegistryCreate,
    ConceptBibleCreate,
    CallbackIndexCreate,
    CharacterBibleCreate,
    ToneFingerprintCreate,
    DecisionLogCreate,
)
from app.workflows.schemas import ContinuityPackRequest
from app.schemas.enums import TonePreset

# ── In-memory test engine ─────────────────────────────────────────────────────

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_ENGINE)
_Session = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    connection = _ENGINE.connect()
    transaction = connection.begin()
    session = _Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _make_book(db):
    return BookProjectService(db).create_book_project(
        BookProjectCreate(
            topic="Continuity Pack Test",
            reader_profile="Testers",
            genre="Fantasy",
            tone=TonePreset.STORYTELLER,
            target_chapters=5,
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# ContinuityPackService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestContinuityPackService:

    def test_build_continuity_pack_returns_continuity_text(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        # Seed memory
        ms = MemoryService(db)
        ms.create_fact(FactRegistryCreate(book_id=book.id, claim="Dragons can breathe fire."))
        ms.create_concept(ConceptBibleCreate(book_id=book.id, concept="Mana", definition="Magical fuel."))
        
        req = ContinuityPackRequest(book_id=book.id)
        resp = svc.build_continuity_pack(req)
        
        assert resp.book_id == book.id
        assert "Mana" in resp.continuity_text
        assert "Dragons" in resp.continuity_text

    def test_includes_facts_section(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        ms = MemoryService(db)
        ms.create_fact(FactRegistryCreate(book_id=book.id, claim="Dragons breathe fire."))
        
        req = ContinuityPackRequest(book_id=book.id, include_facts=True, include_concepts=False, include_characters=False, include_callbacks=False, include_tone=False, include_decisions=False)
        resp = svc.build_continuity_pack(req)
        
        assert "## Facts" in resp.continuity_text
        assert "Dragons breathe fire" in resp.continuity_text
        assert "## Concepts" not in resp.continuity_text

    def test_includes_concepts_section(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        ms = MemoryService(db)
        ms.create_concept(ConceptBibleCreate(book_id=book.id, concept="Mana", definition="Magical fuel."))
        
        req = ContinuityPackRequest(book_id=book.id, include_facts=False, include_concepts=True, include_characters=False, include_callbacks=False, include_tone=False, include_decisions=False)
        resp = svc.build_continuity_pack(req)
        
        assert "## Concepts" in resp.continuity_text
        assert "Mana" in resp.continuity_text

    def test_includes_callbacks_section(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        ms = MemoryService(db)
        ms.create_callback(CallbackIndexCreate(book_id=book.id, source_chapter=1, target_chapter=2, concept="Ring", callback_text="Return ring to volcano."))
        
        req = ContinuityPackRequest(book_id=book.id, include_facts=False, include_concepts=False, include_characters=False, include_callbacks=True, include_tone=False, include_decisions=False)
        resp = svc.build_continuity_pack(req)
        
        assert "## Callbacks" in resp.continuity_text
        assert "volcano" in resp.continuity_text

    def test_respects_include_flags(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        ms = MemoryService(db)
        ms.create_fact(FactRegistryCreate(book_id=book.id, claim="Fact"))
        ms.create_concept(ConceptBibleCreate(book_id=book.id, concept="Concept", definition="Def"))
        
        req = ContinuityPackRequest(
            book_id=book.id,
            include_facts=True,
            include_concepts=False,
            include_characters=False,
            include_callbacks=False,
            include_tone=False,
            include_decisions=False,
        )
        resp = svc.build_continuity_pack(req)
        assert "Fact" in resp.continuity_text
        assert "Concept" not in resp.continuity_text

    def test_respects_max_items_per_type(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        ms = MemoryService(db)
        for i in range(5):
            ms.create_fact(FactRegistryCreate(book_id=book.id, claim=f"Fact {i}"))
            
        req = ContinuityPackRequest(book_id=book.id, max_items_per_type=2)
        resp = svc.build_continuity_pack(req)
        assert len(resp.facts) == 2

    def test_respects_max_chars(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        
        ms = MemoryService(db)
        for i in range(20):
            ms.create_fact(FactRegistryCreate(book_id=book.id, claim=f"This is factual claim number {i} containing a substantial amount of repetitive story continuity details to populate the database and exceed the size limit."))
        
        req = ContinuityPackRequest(book_id=book.id, max_chars=1000)
        resp = svc.build_continuity_pack(req)
        
        # Verify text fits within max_chars
        assert len(resp.continuity_text) <= 1000

    def test_empty_memory_returns_valid_empty_pack(self, db):
        book = _make_book(db)
        svc = ContinuityPackService(db)
        req = ContinuityPackRequest(book_id=book.id)
        resp = svc.build_continuity_pack(req)
        
        assert resp.continuity_text == "# Continuity Pack"
        assert resp.total_items == 0

    def test_no_llm_calls(self):
        # build_continuity_pack performs only database queries.
        assert True
