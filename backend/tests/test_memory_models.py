from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.book import BookProject
from app.models.chapter import Chapter
from app.models.document import SourceDocument, DocumentChunk
from app.models.memory import (
    FactRegistry,
    ConceptBible,
    CharacterBible,
    CallbackIndex,
    ToneFingerprint,
    DecisionLog,
)


def test_base_metadata_contains_memory_tables():
    """Verify that all memory tables are registered in SQLAlchemy metadata."""
    expected_tables = {
        "fact_registry",
        "concept_bible",
        "character_bible",
        "callback_index",
        "tone_fingerprints",
        "decision_log",
    }
    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_memory_models_lifecycle():
    """Verify instantiation, relationships, cascades, and constraints on SQLite."""
    # Setup in-memory SQLite database for isolated unit test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. Instantiate BookProject
        project = BookProject(
            topic="Beginner Personal Finance Guide",
            reader_profile="Young adults aged 18-25 seeking basic budget tips",
            genre="Finance",
            tone="Conversational",
            target_chapters=10,
            words_per_chapter=2000,
            status="created",
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # 2. Instantiate Chapter
        chapter = Chapter(
            book_id=project.id,
            chapter_number=1,
            title="Introduction to Saving",
            summary="Intro text.",
            status="planned",
        )
        session.add(chapter)
        session.commit()
        session.refresh(chapter)

        # 3. Instantiate SourceDocument and DocumentChunk
        doc = SourceDocument(
            book_id=project.id,
            title="Source Document",
            source_type="uploaded_pdf",
            status="created",
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        chunk = DocumentChunk(
            document_id=doc.id,
            book_id=project.id,
            chunk_index=0,
            chunk_text="Source chunk text",
            embedding_status="pending",
        )
        session.add(chunk)
        session.commit()
        session.refresh(chunk)

        # 4. Instantiate FactRegistry
        fact = FactRegistry(
            book_id=project.id,
            chapter_id=chapter.id,
            claim="Compound interest is helpful.",
            source_document_id=doc.id,
            source_chunk_id=chunk.id,
            confidence=0.95,
            status="verified",
            used_in_chapters=[1, 2],
            fact_metadata={"checked_by": "FactCheckerAgent"},
        )
        session.add(fact)
        session.commit()
        session.refresh(fact)

        assert isinstance(fact.id, uuid.UUID)
        assert fact.book_id == project.id
        assert fact.chapter_id == chapter.id
        assert fact.claim == "Compound interest is helpful."
        assert fact.source_document_id == doc.id
        assert fact.source_chunk_id == chunk.id
        assert fact.confidence == 0.95
        assert fact.status == "verified"
        assert fact.used_in_chapters == [1, 2]
        assert fact.fact_metadata == {"checked_by": "FactCheckerAgent"}
        assert fact.book == project
        assert fact.chapter == chapter
        assert fact.source_document == doc
        assert fact.source_chunk == chunk
        assert fact in project.facts
        assert fact in chapter.facts
        assert isinstance(fact.created_at, datetime)
        assert isinstance(fact.updated_at, datetime)

        # 5. Instantiate ConceptBible
        concept = ConceptBible(
            book_id=project.id,
            concept="Compound Interest",
            definition="Interest earned on interest.",
            first_chapter=1,
            related_terms=["savings", "interest"],
            appears_in_chapters=[1, 3],
            concept_metadata={"difficulty": "easy"},
        )
        session.add(concept)
        session.commit()
        session.refresh(concept)

        assert isinstance(concept.id, uuid.UUID)
        assert concept.book_id == project.id
        assert concept.concept == "Compound Interest"
        assert concept.definition == "Interest earned on interest."
        assert concept.first_chapter == 1
        assert concept.related_terms == ["savings", "interest"]
        assert concept.appears_in_chapters == [1, 3]
        assert concept.concept_metadata == {"difficulty": "easy"}
        assert concept.book == project
        assert concept in project.concepts

        # 6. Instantiate CharacterBible
        character = CharacterBible(
            book_id=project.id,
            character_name="Bob the Saver",
            role="Protagonist",
            traits=["frugal", "smart"],
            relationships={"friend": "Alice"},
            arc_summary="Learns to budget and achieves financial freedom.",
            appears_in_chapters=[1, 2, 3],
            character_metadata={"age": 25},
        )
        session.add(character)
        session.commit()
        session.refresh(character)

        assert isinstance(character.id, uuid.UUID)
        assert character.book_id == project.id
        assert character.character_name == "Bob the Saver"
        assert character.role == "Protagonist"
        assert character.traits == ["frugal", "smart"]
        assert character.relationships == {"friend": "Alice"}
        assert character.arc_summary == "Learns to budget and achieves financial freedom."
        assert character.appears_in_chapters == [1, 2, 3]
        assert character.character_metadata == {"age": 25}
        assert character.book == project
        assert character in project.characters

        # 7. Instantiate CallbackIndex
        callback = CallbackIndex(
            book_id=project.id,
            source_chapter=1,
            target_chapter=3,
            concept="Piggy Bank Metaphor",
            callback_text="Remember Bob's dusty piggy bank from chapter 1...",
            status="active",
            callback_metadata={"type": "joke"},
        )
        session.add(callback)
        session.commit()
        session.refresh(callback)

        assert isinstance(callback.id, uuid.UUID)
        assert callback.book_id == project.id
        assert callback.source_chapter == 1
        assert callback.target_chapter == 3
        assert callback.concept == "Piggy Bank Metaphor"
        assert callback.callback_text == "Remember Bob's dusty piggy bank from chapter 1..."
        assert callback.status == "active"
        assert callback.callback_metadata == {"type": "joke"}
        assert callback.book == project
        assert callback in project.callbacks

        # 8. Instantiate ToneFingerprint
        tone = ToneFingerprint(
            book_id=project.id,
            tone_name="FrugalConversational",
            sentence_rhythm={"average_length": 12},
            lexical_rules={"use_words": ["saving", "budget"]},
            banned_phrases=["spend like crazy"],
            example_phrases=["Every penny counts."],
            fingerprint_metadata={"editor": "ToneEditorAgent"},
        )
        session.add(tone)
        session.commit()
        session.refresh(tone)

        assert isinstance(tone.id, uuid.UUID)
        assert tone.book_id == project.id
        assert tone.tone_name == "FrugalConversational"
        assert tone.sentence_rhythm == {"average_length": 12}
        assert tone.lexical_rules == {"use_words": ["saving", "budget"]}
        assert tone.banned_phrases == ["spend like crazy"]
        assert tone.example_phrases == ["Every penny counts."]
        assert tone.fingerprint_metadata == {"editor": "ToneEditorAgent"}
        assert tone.book == project
        assert tone in project.tone_fingerprints

        # 9. Instantiate DecisionLog
        decision = DecisionLog(
            book_id=project.id,
            decision="Postpone complex plots.",
            reason="Simplicity is better for beginners.",
            impact="Reduced word count requirements.",
            decision_metadata={"logged_by": "PlannerAgent"},
        )
        session.add(decision)
        session.commit()
        session.refresh(decision)

        assert isinstance(decision.id, uuid.UUID)
        assert decision.book_id == project.id
        assert decision.decision == "Postpone complex plots."
        assert decision.reason == "Simplicity is better for beginners."
        assert decision.impact == "Reduced word count requirements."
        assert decision.decision_metadata == {"logged_by": "PlannerAgent"}
        assert decision.book == project
        assert decision in project.decision_logs

        # 10. Verify ConceptBible Unique Constraint (book_id + concept)
        duplicate_concept = ConceptBible(
            book_id=project.id,
            concept="Compound Interest",
            definition="Duplicate concept definition.",
        )
        session.add(duplicate_concept)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 11. Verify CharacterBible Unique Constraint (book_id + character_name)
        duplicate_character = CharacterBible(
            book_id=project.id,
            character_name="Bob the Saver",
            role="Duplicate role",
        )
        session.add(duplicate_character)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 12. Check cascade delete behavior
        session.delete(project)
        session.commit()

        # All memory records linked to the project should be deleted
        assert session.query(FactRegistry).filter_by(book_id=project.id).count() == 0
        assert session.query(ConceptBible).filter_by(book_id=project.id).count() == 0
        assert session.query(CharacterBible).filter_by(book_id=project.id).count() == 0
        assert session.query(CallbackIndex).filter_by(book_id=project.id).count() == 0
        assert session.query(ToneFingerprint).filter_by(book_id=project.id).count() == 0
        assert session.query(DecisionLog).filter_by(book_id=project.id).count() == 0
