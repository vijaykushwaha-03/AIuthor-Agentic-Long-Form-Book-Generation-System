# AIuthor Architecture Summary

- **Book Project ID**: `1e536690-7dfe-414d-87ae-44dc1463cbe9`
- **Workflow Run ID**: `a81b2164-fbcf-41b6-80fa-518cecaeb8e1`

This document provides an overview of the AIuthor Long-Form Book Generation System architecture.

## Core Backend Stack
- **FastAPI Backend**: Provides asynchronous, type-safe API routing with automatic OpenAPI generation.
- **PostgreSQL 16 + pgvector**: Stores book projects, chapters, memory registries, and pgvector-backed semantic chunk embeddings.
- **SQLAlchemy 2.0 & Alembic**: Implements strong model typing and manages database migration schemas.

## Cognitive Architecture & Workflows
- **Agentic Orchestration**: Governed by structured prompts for 8 core agents (Planner, Researcher, Writer, Humanizer, Editor, Fact Checker, Memory Keeper, Assembler).
- **LangGraph Pipelines**: Manages conditional branching and state verification during multi-agent book runs.
- **RAG Retrieval Engine**: Performs hybrid keyword-semantic queries against pre-registered source reference materials.

## Observability & Quality Assurance
- **Execution Tracing**: Detailed AgentTrace logs track inputs, outputs, errors, and agent statuses sequentially.
- **Token & Cost Ledgers**: Records model parameters and billing counts per request for auditing.
- **Automated Evaluations**: Validates structural requirements including chapter sequencing and memory continuity.