#!/usr/bin/env python
"""AIuthor Backend — Populate Test Data Script.

Populates the PostgreSQL 16 database with a sample BookProject, BookRun,
SourceDocuments, DocumentChunks, and 768-dimension mock embeddings.
"""
from __future__ import annotations

import sys
import os
import uuid
import random
from datetime import datetime

# Add parent directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database import get_engine
from app.models.book import BookProject
from app.models.run import BookRun
from app.models.document import SourceDocument, DocumentChunk


def generate_mock_vector(dim: int = 768) -> list[float]:
    """Generate a pseudo-random normalized vector of the given dimension."""
    vec = [random.uniform(-1.0, 1.0) for _ in range(dim)]
    length = sum(x * x for x in vec) ** 0.5
    if length == 0.0:
        vec[0] = 1.0
        length = 1.0
    return [x / length for x in vec]


def main():
    print("Connecting to PostgreSQL database to populate test data...")
    try:
        engine = get_engine()
        session = Session(bind=engine)
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Check if we already have test data to avoid duplicating
        existing_project = session.query(BookProject).filter(BookProject.topic.like("%RAG Context Guide%")).first()
        if existing_project:
            print("INFO: Test data already exists. Cleared existing project for clean refresh.")
            session.delete(existing_project)
            session.commit()

        # 1. Create a Book Project
        print("Creating a sample BookProject...")
        project = BookProject(
            id=uuid.uuid4(),
            topic="Long-Form Agentic Book Generation and RAG Context Guides",
            reader_profile="Software engineers and AI practitioners",
            genre="Technical Guides",
            tone="Informative and Educational",
            target_chapters=5,
            words_per_chapter=1200,
            status="created",
            project_metadata={"tags": ["RAG", "Agents", "FastAPI", "Postgres"]}
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        print(f"BookProject created with ID: {project.id}")

        # 2. Create a Book Run
        print("Creating a sample BookRun...")
        run = BookRun(
            id=uuid.uuid4(),
            book_id=project.id,
            status="completed",
            current_agent="ResearcherAgent",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            run_metadata={"completed_by": "mock_setup"}
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        print(f"BookRun created with ID: {run.id}")

        # 3. Create Source Documents
        print("Creating sample SourceDocuments...")
        doc1 = SourceDocument(
            id=uuid.uuid4(),
            book_id=project.id,
            title="Understanding Retrieval-Augmented Generation (RAG)",
            source_type="Research Paper",
            source_url="https://example.com/rag-paper.pdf",
            raw_text="Retrieval-Augmented Generation (RAG) is a technique that combines retrieval models with generative models to produce factual texts.",
            status="completed",
            document_metadata={"author": "AI Research Group"}
        )
        
        doc2 = SourceDocument(
            id=uuid.uuid4(),
            book_id=project.id,
            title="Agentic Frameworks and Multi-Agent Orchestration",
            source_type="Documentation",
            source_url="https://example.com/agents-guide.html",
            raw_text="Agentic frameworks use graphs and state machines to manage agent executions and self-healing error repair loops.",
            status="completed",
            document_metadata={"author": "Framework Team"}
        )
        
        session.add_all([doc1, doc2])
        session.commit()
        session.refresh(doc1)
        session.refresh(doc2)
        print("SourceDocuments created successfully.")

        # 4. Create Document Chunks with mock 768-dim embeddings
        print("Creating DocumentChunks with 768-dimension embeddings...")
        
        # Doc 1 Chunks
        chunk_texts_1 = [
            "Retrieval-Augmented Generation (RAG) integrates retrieval mechanism with generative pre-trained transformers to access factual external documents.",
            "Standard vector databases store chunks using high-dimensional dense vectors and index them using algorithms like HNSW or IVFFlat.",
            "Lexical searches use traditional keyword indexing like TF-IDF or BM25 to match exact phrases and terms in text corpus."
        ]
        
        # Doc 2 Chunks
        chunk_texts_2 = [
            "Multi-agent frameworks use directed acyclic graphs (DAGs) and state machine loops to handle complex reasoning tasks.",
            "Error recovery and repair loops allow writing agents to fix formatting issues, insert chapters, and verify character consistency.",
            "A concept bible acts as a persistent memory registry keeping trace of callback terms, narrative rules, and glossary items."
        ]

        chunks = []
        for i, text_val in enumerate(chunk_texts_1):
            chunks.append(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc1.id,
                    book_id=project.id,
                    chunk_index=i,
                    chunk_text=text_val,
                    token_count=len(text_val.split()),
                    embedding_model="text-embedding-004",
                    embedding_status="completed",
                    embedding=generate_mock_vector(768),
                    embedding_provider="mock",
                    embedding_dimensions=768,
                    embedding_created_at=datetime.utcnow(),
                    chunk_metadata={"doc_index": i}
                )
            )

        for i, text_val in enumerate(chunk_texts_2):
            chunks.append(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc2.id,
                    book_id=project.id,
                    chunk_index=i,
                    chunk_text=text_val,
                    token_count=len(text_val.split()),
                    embedding_model="text-embedding-004",
                    embedding_status="completed",
                    embedding=generate_mock_vector(768),
                    embedding_provider="mock",
                    embedding_dimensions=768,
                    embedding_created_at=datetime.utcnow(),
                    chunk_metadata={"doc_index": i}
                )
            )

        session.add_all(chunks)
        session.commit()
        print(f"Created {len(chunks)} chunks with native embeddings in PostgreSQL.")
        
        print("\nSUCCESS: PostgreSQL 16 is now populated with real test data!")
        print(f"BookProject ID: {project.id}")
        print(f"SourceDocument 1 ID: {doc1.id}")
        print(f"SourceDocument 2 ID: {doc2.id}")
        
    except Exception as e:
        session.rollback()
        print(f"ERROR: Failed to populate data: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
