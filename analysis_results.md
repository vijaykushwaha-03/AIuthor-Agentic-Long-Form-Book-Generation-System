# AIuthor Project Requirements Analysis

Based on the provided documents (`AIuthor_Project_Detailed_Module_Breakdown.docx` and `AIuthor_Antigravity_Implementation_Plan.pdf`), here is a detailed, step-by-step analysis of the project requirements, architecture, and implementation strategy.

## 1. Project Purpose & Scope
**AIuthor** is an agentic long-form book generation system. It takes a user brief (topic, reader profile, length, tonality, genre) and produces a publication-ready book. The core objective is **not** to prove an LLM can write text, but to demonstrate a robust engineering system that orchestrates multiple agents, manages memory outside the context window, grounds factual claims, evaluates outputs, and repairs dependent content when the book structure changes.

## 2. Target Architecture & Tech Stack
The project mandates a modern, production-ready stack:
*   **Frontend**: React + Vite + Tailwind CSS (Fast, clean UI, easy state management).
*   **Backend**: FastAPI (Async APIs, strict Pydantic models).
*   **Database**: PostgreSQL for transactional data (books, runs, chapters, memory, traces, logs).
*   **Vector DB**: `pgvector` for semantic search and RAG document chunks.
*   **Orchestration**: LangGraph for stateful multi-agent execution, routing, retries, and repair loops.
*   **Export**: `python-docx` for Word documents and LibreOffice headless for PDF conversion.

## 3. Core Requirements & Engineering Principles
1.  **Backend-First Implementation**: Build the API, database, orchestration, and agents before adding a React UI.
2.  **Multi-Agent Workflow**: Avoid "giant prompts". Use distinct, coordinated agents:
    *   *Planner*: Outlines the book and chapter contracts.
    *   *Researcher*: Retrieves evidence via pgvector.
    *   *Writer*: Drafts chapters avoiding unsupported claims.
    *   *Humanizer*: Removes "AI tells" and improves rhythm.
    *   *Editor*: Improves structure and grammar.
    *   *Fact Checker*: Compares claims with evidence, triggering repairs if needed.
    *   *Memory Keeper*: Extracts and updates facts, concepts, and characters into DB tables.
    *   *Assembler*: Compiles the final book.
3.  **Strict Contracts**: All inputs/outputs between agents must use strict Pydantic schemas.
4.  **Prompt Registry**: Prompts must be stored as real markdown files in a `prompts/` directory, not hardcoded in python files.
5.  **Comprehensive Observability**:
    *   `agent_traces`: Log execution states and summaries.
    *   `prompt_logs`: Log exact rendered prompts and payloads.
    *   `memory_io_logs`: Log every memory read/write operation.
    *   `token_cost_ledger`: Track token usage and estimated costs.
6.  **Persistent Memory**: Manage facts, concepts, characters, callbacks, and tone fingerprints outside the LLM context using PostgreSQL tables.
7.  **Self-Healing Repair (Test D)**: Inserting a new chapter must automatically repair the Table of Contents (TOC), update callback numbers, and regenerate the glossary.
8.  **Automated Evaluations (Evals)**: Implement programmatic quality gates for structure, tone, AI tells, fact grounding, callbacks, and insertion repair.

## 4. Module-by-Module Implementation Plan

The documents prescribe a strict, iterative module-by-module build strategy. **Do not skip modules or build them all at once.**

### Backend Modules
*   **Module 0: Setup**: Repo structure, Docker Compose (Postgres + pgvector, Redis, Backend, Frontend), dependencies.
*   **Module 1: FastAPI Core**: Health checks, CORS, config, DB session, global error handling.
*   **Module 2: Database Layer**: SQLAlchemy models and Alembic migrations for books, memory tables, RAG chunks, and observability tables.
*   **Module 3: Pydantic Schemas**: Strict request/response contracts for APIs and inter-agent communication.
*   **Module 4: Prompt Registry**: Loading and managing prompt files from the filesystem.
*   **Module 5: Observability**: Trace logging, prompt logging, memory I/O logging, and the token cost ledger.
*   **Module 6: RAG Pipeline**: Document ingestion, chunking, embeddings, pgvector cosine similarity retrieval, and evidence pack building.
*   **Module 7: Memory System**: Services for interacting with the fact registry, concept bible, character bible, and callback index.
*   **Module 8: LangGraph Orchestration**: Setting up the state graph, conditional edges (e.g., routing to repair on fact-check failure), and workflow execution.
*   **Module 9: Agent Implementations**: Replacing mock nodes with actual LLM calls using the prompt registry and schemas.
*   **Module 10: Chapter Insertion & Repair**: The self-healing logic. Renumbering chapters, repairing callbacks, and rebuilding the glossary when a chapter is inserted.
*   **Module 11: Export**: Generating DOCX and PDFs with front/back matter and proper pagination.
*   **Module 12: Quality Gates (Evals)**: Automated scoring for tone, AI tells, facts, and structure.
*   **Module 13: Test Case Runners (A-D)**: Scripts to run the 4 mandatory assessment test cases (e.g., Test A: 10-chapter finance guide, Test D: Chapter insertion).

### Frontend Modules
*   **Module 1: React Setup**: Vite, React Router, Tailwind, API client structure.
*   **Module 2: New Book Brief UI**: Form to collect topic, tone, chapters, and launch the LangGraph run.
*   **Module 3: Run Monitor UI**: Real-time/polling view of the LangGraph agent timeline, showing current status and errors.
*   **Module 4: Book Preview UI**: Reading interface for the generated outline, chapters, and sections. Includes UI for inserting a new chapter.
*   **Module 5: Observability & Export UI**: Dashboards to view Memory (facts, concepts), Traces, Prompt Logs, Eval reports, and buttons to download the DOCX/PDF/trace bundles.

## 5. Testing Strategy
Testing is heavily emphasized throughout the plan:
*   **Backend Unit & Integration**: Pytest for schemas, API endpoints, RAG chunks, and export generation.
*   **Agent Schema Tests**: Mocked LLM responses to ensure strict Pydantic output compliance.
*   **Frontend Tests**: React Testing Library for components and Playwright for E2E flows (Create Book -> Monitor Run -> Download Export).

## Next Steps
Following the "Development Rule" from your request: We must implement one module at a time. The recommended starting point is **Backend Module 0 and Module 1** (Repository Setup and FastAPI Core). 

I am ready to begin implementing the first module whenever you give the command.
