"""
AIuthor Backend Tests — MemoryService unit tests.

Tests use a per-test transaction rollback for isolation against in-memory SQLite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import uuid4, UUID

from app.database import Base
import app.models  # noqa: F401

from app.services import (
    BookProjectService,
    ChapterService,
    MemoryService,
    NotFoundError,
    ConflictError,
    ValidationServiceError,
)
from app.schemas import (
    BookProjectCreate,
    ChapterCreate,
    FactRegistryCreate,
    FactRegistryUpdate,
    ConceptBibleCreate,
    ConceptBibleUpdate,
    CharacterBibleCreate,
    CharacterBibleUpdate,
    CallbackIndexCreate,
    CallbackIndexUpdate,
    ToneFingerprintCreate,
    ToneFingerprintUpdate,
    DecisionLogCreate,
    DecisionLogUpdate,
    MemoryReadRequest,
    MemoryWriteRequest,
)
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


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_book(db):
    return BookProjectService(db).create_book_project(
        BookProjectCreate(
            topic="Memory System Test",
            reader_profile="Testers",
            genre="Fiction",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=3,
        )
    )


def _make_chapter(db, book_id, chapter_number=1):
    return ChapterService(db).create_chapter(
        book_id=book_id,
        payload=ChapterCreate(
            book_id=book_id,
            chapter_number=chapter_number,
            title=f"Chapter {chapter_number}",
            summary="A test chapter",
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# FactRegistry Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestFactRegistryService:

    def test_create_fact_creates_fact(self, db):
        book = _make_book(db)
        chapter = _make_chapter(db, book.id)
        svc = MemoryService(db)

        fact = svc.create_fact(
            FactRegistryCreate(
                book_id=book.id,
                chapter_id=chapter.id,
                claim="Water freezes at 0 degrees Celsius.",
                status="unverified",
                confidence=0.95,
            )
        )
        assert fact.id is not None
        assert fact.book_id == book.id
        assert fact.chapter_id == chapter.id
        assert fact.claim == "Water freezes at 0 degrees Celsius."
        assert fact.confidence == 0.95

    def test_get_fact_returns_fact(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        created = svc.create_fact(
            FactRegistryCreate(book_id=book.id, claim="Earth is round.")
        )
        fetched = svc.get_fact(book.id, created.id)
        assert fetched.id == created.id
        assert fetched.claim == "Earth is round."

    def test_list_facts_returns_paginated_records(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_fact(FactRegistryCreate(book_id=book.id, claim="Fact Number One"))
        svc.create_fact(FactRegistryCreate(book_id=book.id, claim="Fact Number Two"))
        
        items, total = svc.list_facts(book.id, page=1, page_size=10)
        assert total == 2
        assert len(items) == 2

    def test_update_fact_changes_status_confidence(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        fact = svc.create_fact(
            FactRegistryCreate(book_id=book.id, claim="Sky is green.", status="unverified", confidence=0.1)
        )
        updated = svc.update_fact(
            book.id, fact.id, FactRegistryUpdate(status="verified", confidence=0.99, claim="Sky is blue.")
        )
        assert updated.status == "verified"
        assert updated.confidence == 0.99
        assert updated.claim == "Sky is blue."

    def test_delete_fact_deletes_fact(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        fact = svc.create_fact(FactRegistryCreate(book_id=book.id, claim="Temporary fact"))
        
        res = svc.delete_fact(book.id, fact.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_fact(book.id, fact.id)

    def test_missing_fact_raises_not_found(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_fact(book.id, uuid4())
        assert exc.value.code == "fact_not_found"


# ══════════════════════════════════════════════════════════════════════════════
# ConceptBible Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestConceptBibleService:

    def test_create_concept_creates_concept(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        concept = svc.create_concept(
            ConceptBibleCreate(book_id=book.id, concept="Hyperdrive", definition="Fasting than light travel system.")
        )
        assert concept.id is not None
        assert concept.concept == "Hyperdrive"

    def test_list_concepts_search_finds_concept(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="Warp Core", definition="Engine fuel."))
        svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="Phaser", definition="Energy weapon."))

        items, total = svc.list_concepts(book.id, search="weapon")
        assert total == 1
        assert items[0].concept == "Phaser"

    def test_update_concept_updates_definition(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        concept = svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="Shields", definition="Defense."))
        updated = svc.update_concept(book.id, concept.id, ConceptBibleUpdate(definition="Energy barriers."))
        assert updated.definition == "Energy barriers."

    def test_delete_concept_deletes_concept(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        concept = svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="Relic", definition="Old object."))
        
        svc.delete_concept(book.id, concept.id)
        with pytest.raises(NotFoundError):
            svc.get_concept(book.id, concept.id)

    def test_duplicate_concept_raises_conflict(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="Chronotons", definition="Time particles."))
        with pytest.raises(ConflictError):
            svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="Chronotons", definition="Another def."))


# ══════════════════════════════════════════════════════════════════════════════
# CharacterBible Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCharacterBibleService:

    def test_create_character_creates_character(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        char = svc.create_character(
            CharacterBibleCreate(book_id=book.id, character_name="Alice", role="Protagonist", traits=["brave"])
        )
        assert char.id is not None
        assert char.character_name == "Alice"
        assert char.traits == ["brave"]

    def test_list_characters_search_finds_character(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="Alice", role="Pilot"))
        svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="Bob", role="Engineer"))

        items, total = svc.list_characters(book.id, search="Pilot")
        assert total == 1
        assert items[0].character_name == "Alice"

    def test_update_character_updates_arc_summary(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        char = svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="Charlie"))
        updated = svc.update_character(book.id, char.id, CharacterBibleUpdate(arc_summary="Becomes a leader."))
        assert updated.arc_summary == "Becomes a leader."

    def test_delete_character_deletes_character(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        char = svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="Dave"))
        svc.delete_character(book.id, char.id)
        with pytest.raises(NotFoundError):
            svc.get_character(book.id, char.id)

    def test_duplicate_character_raises_conflict(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="Eve"))
        with pytest.raises(ConflictError):
            svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="Eve"))


# ══════════════════════════════════════════════════════════════════════════════
# CallbackIndex Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCallbackIndexService:

    def test_create_callback_creates_callback(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        cb = svc.create_callback(
            CallbackIndexCreate(
                book_id=book.id, source_chapter=1, target_chapter=3, concept="Locket", callback_text="She finds the locket again."
            )
        )
        assert cb.id is not None
        assert cb.callback_text == "She finds the locket again."

    def test_list_callbacks_filters_by_source_chapter(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_callback(
            CallbackIndexCreate(book_id=book.id, source_chapter=1, target_chapter=3, callback_text="Callback One")
        )
        svc.create_callback(
            CallbackIndexCreate(book_id=book.id, source_chapter=2, target_chapter=3, callback_text="Callback Two")
        )

        items, total = svc.list_callbacks(book.id, source_chapter=1)
        assert total == 1
        assert items[0].callback_text == "Callback One"

    def test_update_callback_updates_status(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        cb = svc.create_callback(
            CallbackIndexCreate(book_id=book.id, callback_text="Callback Base", status="active")
        )
        updated = svc.update_callback(book.id, cb.id, CallbackIndexUpdate(status="resolved"))
        assert updated.status == "resolved"

    def test_delete_callback_deletes_callback(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        cb = svc.create_callback(CallbackIndexCreate(book_id=book.id, callback_text="Callback Delete"))
        svc.delete_callback(book.id, cb.id)
        with pytest.raises(NotFoundError):
            svc.get_callback(book.id, cb.id)


# ══════════════════════════════════════════════════════════════════════════════
# ToneFingerprint Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestToneFingerprintService:

    def test_create_tone_fingerprint_creates_tone_fingerprint(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        tone = svc.create_tone_fingerprint(
            ToneFingerprintCreate(
                book_id=book.id,
                tone_name=TonePreset.CONVERSATIONAL,
                lexical_rules={"use_contractions": True},
            )
        )
        assert tone.id is not None
        assert tone.tone_name == "conversational"
        assert tone.lexical_rules == {"use_contractions": True}

    def test_list_tone_fingerprints_filters_by_tone_name(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_tone_fingerprint(ToneFingerprintCreate(book_id=book.id, tone_name="formal"))
        svc.create_tone_fingerprint(ToneFingerprintCreate(book_id=book.id, tone_name="conversational"))

        items, total = svc.list_tone_fingerprints(book.id, tone_name="formal")
        assert total == 1
        assert items[0].tone_name == "formal"

    def test_update_tone_fingerprint_updates_lexical_rules(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        tone = svc.create_tone_fingerprint(
            ToneFingerprintCreate(book_id=book.id, tone_name="poetic", lexical_rules={"metaphors": 1})
        )
        updated = svc.update_tone_fingerprint(
            book.id, tone.id, ToneFingerprintUpdate(lexical_rules={"metaphors": 5})
        )
        assert updated.lexical_rules == {"metaphors": 5}

    def test_delete_tone_fingerprint_deletes_tone_fingerprint(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        tone = svc.create_tone_fingerprint(ToneFingerprintCreate(book_id=book.id, tone_name="casual"))
        svc.delete_tone_fingerprint(book.id, tone.id)
        with pytest.raises(NotFoundError):
            svc.get_tone_fingerprint(book.id, tone.id)


# ══════════════════════════════════════════════════════════════════════════════
# DecisionLog Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionLogService:

    def test_create_decision_creates_decision(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        dec = svc.create_decision(
            DecisionLogCreate(book_id=book.id, decision="Use SQLite in-memory", reason="Performance", impact="Faster tests")
        )
        assert dec.id is not None
        assert dec.book_id == book.id
        assert dec.decision == "Use SQLite in-memory"

    def test_list_decisions_filters_by_book_id(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        svc.create_decision(DecisionLogCreate(book_id=book.id, decision="Decision One"))
        svc.create_decision(DecisionLogCreate(book_id=None, decision="Decision Two Global"))

        items, total = svc.list_decisions(book_id=book.id)
        assert total == 1
        assert items[0].decision == "Decision One"

        global_items, global_total = svc.list_decisions(book_id=None)
        assert global_total == 2

    def test_update_decision_updates_impact(self, db):
        svc = MemoryService(db)
        dec = svc.create_decision(DecisionLogCreate(decision="Decision Base", impact="TBD"))
        updated = svc.update_decision(dec.id, DecisionLogUpdate(impact="Huge"))
        assert updated.impact == "Huge"

    def test_delete_decision_deletes_decision(self, db):
        svc = MemoryService(db)
        dec = svc.create_decision(DecisionLogCreate(decision="Temporary Decision"))
        svc.delete_decision(dec.id)
        with pytest.raises(NotFoundError):
            svc.get_decision(dec.id)


# ══════════════════════════════════════════════════════════════════════════════
# Memory Envelope Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMemoryEnvelopeService:

    def test_read_memory_returns_all_groups(self, db):
        book = _make_book(db)
        svc = MemoryService(db)

        # Seed data
        svc.create_fact(FactRegistryCreate(book_id=book.id, claim="Fact Number One"))
        svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="ConceptOne", definition="DefinitionOne"))
        svc.create_character(CharacterBibleCreate(book_id=book.id, character_name="CharacterOne"))
        svc.create_callback(CallbackIndexCreate(book_id=book.id, callback_text="Callback Text One"))
        svc.create_tone_fingerprint(ToneFingerprintCreate(book_id=book.id, tone_name="ToneOne"))
        svc.create_decision(DecisionLogCreate(book_id=book.id, decision="Decision One"))

        resp = svc.read_memory(MemoryReadRequest(book_id=book.id))
        assert resp.total_items == 6
        assert len(resp.facts) == 1
        assert len(resp.concepts) == 1
        assert len(resp.characters) == 1
        assert len(resp.callbacks) == 1
        assert len(resp.tone_fingerprints) == 1
        assert len(resp.decisions) == 1

    def test_read_memory_with_memory_types_filters_groups(self, db):
        book = _make_book(db)
        svc = MemoryService(db)

        svc.create_fact(FactRegistryCreate(book_id=book.id, claim="Fact Number One"))
        svc.create_concept(ConceptBibleCreate(book_id=book.id, concept="ConceptOne", definition="DefinitionOne"))

        resp = svc.read_memory(MemoryReadRequest(book_id=book.id, memory_types=["facts"]))
        assert resp.total_items == 1
        assert len(resp.facts) == 1
        assert len(resp.concepts) == 0

    def test_write_memory_creates_fact_and_concept_and_returns_created_counts(self, db):
        book = _make_book(db)
        svc = MemoryService(db)

        write_req = MemoryWriteRequest(
            book_id=book.id,
            facts=[FactRegistryCreate(book_id=book.id, claim="WriteFact")],
            concepts=[ConceptBibleCreate(book_id=book.id, concept="WriteConcept", definition="WCD")],
        )
        resp = svc.write_memory(write_req)
        assert resp.created_counts["facts"] == 1
        assert resp.created_counts["concepts"] == 1
        assert resp.status == "completed"

        # Verify items exist in DB
        facts, _ = svc.list_facts(book.id)
        assert len(facts) == 1
        assert facts[0].claim == "WriteFact"


# ══════════════════════════════════════════════════════════════════════════════
# Error & Edge Cases Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMemoryServiceErrors:

    def test_create_fact_for_missing_book_raises_not_found(self, db):
        svc = MemoryService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.create_fact(FactRegistryCreate(book_id=uuid4(), claim="No book"))
        assert exc.value.code == "book_not_found"

    def test_create_fact_with_missing_chapter_id_raises_not_found(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.create_fact(FactRegistryCreate(book_id=book.id, chapter_id=uuid4(), claim="Bad chapter"))
        assert exc.value.code == "chapter_not_found"

    def test_get_missing_record_raises_not_found(self, db):
        book = _make_book(db)
        svc = MemoryService(db)
        with pytest.raises(NotFoundError):
            svc.get_concept(book.id, uuid4())
        with pytest.raises(NotFoundError):
            svc.get_character(book.id, uuid4())
        with pytest.raises(NotFoundError):
            svc.get_callback(book.id, uuid4())
        with pytest.raises(NotFoundError):
            svc.get_tone_fingerprint(book.id, uuid4())

    def test_write_memory_mismatch_book_id_raises_validation_error(self, db):
        book = _make_book(db)
        svc = MemoryService(db)

        write_req = MemoryWriteRequest(
            book_id=book.id,
            facts=[FactRegistryCreate(book_id=uuid4(), claim="Mismatch")],
        )
        with pytest.raises(ValidationServiceError) as exc:
            svc.write_memory(write_req)
        assert exc.value.code == "book_id_mismatch"
