#!/usr/bin/env python
"""AIuthor Backend — Database Seeding Script.

Populates the real PostgreSQL database with realistic development data,
including a BookProject, SourceDocument, DocumentChunks, and related entries.
"""
from __future__ import annotations

import sys
import os
import uuid
from datetime import datetime, timezone

# Add parent directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database import get_session_local, ping_db
from app.models import (
    BookProject,
    SourceDocument,
    DocumentChunk,
    FactRegistry,
    ConceptBible,
    CharacterBible,
)


def seed_database():
    print("Verifying database connection...")
    try:
        ping_db()
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

    SessionLocal = get_session_local()
    db: Session = SessionLocal()

    try:
        print("Seeding database...")

        # 1. Create a sample Book Project
        book = BookProject(
            id=uuid.uuid4(),
            topic="The Exploration of Mars: Science, Fiction, and Our Multiplanetary Future",
            reader_profile="General science enthusiasts, amateur astronomers, and space exploration fans.",
            genre="Science Non-Fiction / Narrative Non-Fiction",
            tone="Inspiring, Educational, Visionary",
            target_chapters=10,
            words_per_chapter=3500,
            status="created",
            project_metadata={
                "target_completion": "2026-12-31",
                "focus_areas": ["robotic rovers", "manned missions", "terraforming", "historical myths"]
            }
        )
        db.add(book)
        db.flush()  # Get book.id referenced below
        print(f"Created BookProject: '{book.topic}' (ID: {book.id})")

        # 2. Create a couple of Characters (for Character Bible)
        char1 = CharacterBible(
            id=uuid.uuid4(),
            book_id=book.id,
            character_name="Dr. Sarah Chen",
            role="Lead Astrobiologist (Fictionalized Subject)",
            traits=["passionate", "precise", "protective"],
            arc_summary="Sarah shifts from studying extremophiles on Earth to orchestrating the first biological searches on Mars, overcoming planetary protection dilemmas.",
            relationships={"Dr. Marcus Vance": "Colleague / Professional Rival"},
            character_metadata={"field_experience": "Atacama & Antarctica"}
        )
        char2 = CharacterBible(
            id=uuid.uuid4(),
            book_id=book.id,
            character_name="Dr. Marcus Vance",
            role="Mission Director (Fictionalized Subject)",
            traits=["pragmatic", "authoritative", "focused"],
            arc_summary="Marcus navigates the massive logistical, financial, and geopolitical pressures of launching the Ares-I human mission to Mars.",
            relationships={"Dr. Sarah Chen": "Professional Colleague"},
            character_metadata={"former_role": "NASA JPL Flight Director"}
        )
        db.add_all([char1, char2])

        # 3. Create a Concept Bible Entry
        concept = ConceptBible(
            id=uuid.uuid4(),
            book_id=book.id,
            concept="Planetary Protection Policy (PPP)",
            definition="A set of internationally agreed guidelines to prevent forward contamination (Earth microbes infecting Mars) and backward contamination (Martian materials infecting Earth).",
            first_chapter=2,
            concept_metadata={"regulating_body": "COSPAR"}
        )
        db.add(concept)

        # 4. Create a Fact Registry Entry
        fact = FactRegistry(
            id=uuid.uuid4(),
            book_id=book.id,
            claim="Mars has approximately 38% of the surface gravity of Earth.",
            confidence=1.0,
            status="verified",
            fact_metadata={
                "surface_gravity_m_s2": 3.71,
                "evidence_citation": "NASA Mars Fact Sheet (2024)"
            }
        )
        db.add(fact)

        # 5. Create a Source Document
        doc = SourceDocument(
            id=uuid.uuid4(),
            book_id=book.id,
            title="NASA Mars Exploration Rover Mission Overview",
            source_type="Research Paper",
            source_url="https://mars.nasa.gov/mer/mission/overview/",
            raw_text="The Mars Exploration Rover mission set out to study the history of water on Mars. Spirit and Opportunity were two robotic rovers sent to search for clues of past water activity. The mission proved that liquid water once flowed on the red planet's surface.",
            status="processed"
        )
        db.add(doc)
        db.flush()

        # 6. Create Document Chunks with realistic embeddings
        mock_embedding_1 = [0.01 * (i % 10) for i in range(768)]
        mock_embedding_2 = [-0.01 * (i % 10) for i in range(768)]

        chunk1 = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            book_id=book.id,
            chunk_index=0,
            chunk_text="The Mars Exploration Rover (MER) mission was a robotic space mission involving two Mars rovers, Spirit (MER-A) and Opportunity (MER-B), exploring the planet Mars.",
            token_count=32,
            chunk_metadata={"rover": "Spirit & Opportunity"},
            embedding_model="text-embedding-004",
            embedding_status="completed",
            embedding=mock_embedding_1,
            embedding_provider="gemini",
            embedding_dimensions=768,
            embedding_created_at=datetime.now(timezone.utc),
            embedding_error=None
        )

        chunk2 = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            book_id=book.id,
            chunk_index=1,
            chunk_text="The mission's scientific objective was to search for and characterize a wide range of rocks and soils that hold clues to past water activity on Mars.",
            token_count=31,
            chunk_metadata={"objective": "Past water search"},
            embedding_model="text-embedding-004",
            embedding_status="completed",
            embedding=mock_embedding_2,
            embedding_provider="gemini",
            embedding_dimensions=768,
            embedding_created_at=datetime.now(timezone.utc),
            embedding_error=None
        )

        chunk3 = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            book_id=book.id,
            chunk_index=2,
            chunk_text="Opportunity remained active for nearly 15 years, far exceeding its planned 90-day lifetime, before sending its final transmission in 2018.",
            token_count=25,
            chunk_metadata={"rover": "Opportunity", "lifespan": "15 years"},
            embedding_model=None,
            embedding_status="pending",
            embedding=None,
            embedding_provider=None,
            embedding_dimensions=None,
            embedding_created_at=None,
            embedding_error=None
        )

        db.add_all([chunk1, chunk2, chunk3])

        db.commit()
        print("Database successfully seeded!")
        print("\nCreated Development Records:")
        print(f"- 1 Book Project: {book.topic}")
        print(f"- 2 Character Bible Entries: Dr. Sarah Chen, Dr. Marcus Vance")
        print(f"- 1 Concept Bible Entry: Planetary Protection Policy")
        print(f"- 1 Fact Registry Entry: Gravity comparison")
        print(f"- 1 Source Document: {doc.title}")
        print(f"- 3 Document Chunks (2 embedded successfully, 1 pending embedding)")
        print("\n🎉 You can now open http://localhost:8000/admin/ to see all this data live!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
