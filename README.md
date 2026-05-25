# ✍️ AIuthor — Agentic Long-Form Book Generation System

AIuthor is a production-grade, state-of-the-art agentic system designed to generate publication-ready books from a structured user brief. Orchestrated via **LangGraph**, it runs a sequential multi-agent loop backed by a **PostgreSQL + pgvector** memory layer for factual continuity, RAG, and document assembly, exporting fully polished manuscripts to **DOCX/PDF**.

---

## 🚀 Key Features

* **Multi-Agent Orchestration**: Eight cooperative agents (Planner, Researcher, Writer, Humanizer, Editor, Fact Checker, Memory Keeper, and Assembler) working in tandem via LangGraph.
* **Continuity & Memory System**: Relational PostgreSQL database storing lore bibles (Characters, Concepts, Facts, Callbacks, and Tone Fingerprints) to guarantee consistency across chapters.
* **Hybrid RAG Layer**: Combined lexical (BM25 keyword) and semantic (Gemini vector embeddings via pgvector) retrieval for fact-grounding.
* **JSON Leak & Injection Shield**: Advanced manuscript cleaners to prevent prompt instructions, raw JSON envelopes, formatting blocks, or code fences from leaking into the final prose.
* **Professional Document Export**: Compiles completed chapters into a publication-ready DOCX with front matter, copyright information, Table of Contents, glossary, and bibliography.

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend Framework** | FastAPI + Pydantic v2 |
| **Database & Memory** | PostgreSQL 16/18 + `pgvector` |
| **Workflow Graph** | LangGraph |
| **LLM Providers** | NVIDIA NIM AI Endpoints (`meta/llama-3.3-70b-instruct` / Gemini-2.5) |
| **Doc Exporting** | `python-docx` + LibreOffice PDF converter |
| **Testing** | Pytest |

---

## 📂 Project Directory Structure

```text
AIuthor-Agentic-Long-Form-Book-Generation-System/
├── backend/
│   ├── app/
│   │   ├── api/                 # Endpoint routers (health, books, runs, exports, etc.)
│   │   ├── models/              # SQLAlchemy database ORM models (observability & lore bibles)
│   │   ├── schemas/             # Pydantic data schemas for API requests/responses
│   │   ├── services/            # Core business logic layer (generation loops, exports, evals)
│   │   ├── utils/               # Sanitizers, parsers, and text cleaning utilities
│   │   ├── workflows/           # LangGraph pipeline definition, agent nodes, and graph states
│   │   └── database.py          # SQLAlchemy engine and session dependency
│   ├── docs/                    # Detailed engineering architecture and module docs
│   ├── prompts/                 # Standardized prompt dossiers for all agents
│   ├── storage/                 # Local directory for exported books and programmatic reports
│   ├── generate_new_book.py     # End-to-end book generation automation script
│   ├── requirements.txt         # Pinned Python dependencies
│   └── pyproject.toml           # Pytest settings
├── DELIVERABLES/                # Compiled HR submission folder containing checklist items
│   ├── sample_books/            # Generated sample manuscripts in DOCX format
│   ├── README.md                # Delivery mapping checklist
│   ├── ARCHITECTURE.md          # Multi-agent topology and RAG flow
│   ├── MEMORY_SCHEMA.md         # Database tables and sample JSON records
│   ├── EVALS_REPORT.md          # Scorecard with LLM-as-judge evaluations
│   └── PROMPTS_DOSSIER.md       # Full prompt collection for all agents
└── README.md                    # Root project documentation (this file)
```

---

## ⚙️ Local Setup Guide

Follow these steps to run the backend and execute the book generator locally.

### 1. Database Configuration (PostgreSQL 16/18)
Ensure PostgreSQL (with the `pgvector` extension) is installed and running on port `5433` (or update `.env`).

Connect to your database instance and run:
```sql
CREATE USER aiuthor WITH PASSWORD 'aiuthor_secret' CREATEDB;
CREATE DATABASE aiuthor_db OWNER aiuthor;
```

### 2. Python Environment Setup
Navigate to the backend directory, initialize a virtual environment, and install all dependencies:
```powershell
cd backend
python -m venv .venv

# On Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# On Windows (CMD)
.\.venv\Scripts\activate.bat

# On Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment File Configuration
Copy the template `.env` and enter your API keys:
```powershell
copy .env.example .env
```
Key configuration settings in `.env`:
* `LLM_PROVIDER=nvidia`
* `NVIDIA_API_KEY=your-nvidia-nim-key`
* `GEMINI_API_KEY=your-gemini-key`
* `DATABASE_URL=postgresql+psycopg2://aiuthor:aiuthor_secret@127.0.0.1:5433/aiuthor_db`

---

## 🏃 Running the Book Generation Script

To run a full end-to-end book generation, export, evaluation, and packaging loop, run the automation script:

```powershell
$env:PYTHONPATH="."
python generate_new_book.py
```

This script will automate the following operations:
1. **Initialize** the database schema.
2. **Create** the book project: *"Architecting Modern Retrieval-Augmented Generation Systems"*.
3. **Plan and create** 3 target chapters in the PostgreSQL database.
4. **Trigger the sequential LangGraph pipeline** in `real_dev` execution mode.
5. **Export** the final clean book manuscript into DOCX.
6. **Compile** trace summaries, memory reports, and token/cost ledgers.

To copy the fresh results into the HR delivery folder:
```powershell
python C:\Users\Vijay\.gemini\antigravity-ide\brain\b578ce44-60e6-4450-8e87-ab7db2ddaa2f\scratch\compile_submission.py
```

---

## 🧪 Running Unit & Integration Tests

The test suite runs on an in-memory SQLite database configuration—**no local Postgres instance is required** for testing.

```powershell
# From the backend/ directory with .venv active
python -m pytest tests/ -v
```

---

## 🔍 Connection & API Overview

| Service | Address |
| :--- | :--- |
| **FastAPI Backend Base** | `http://127.0.0.1:8000` |
| **Interactive Swagger API Docs** | `http://127.0.0.1:8000/docs` |
| **PostgreSQL Database Host** | `127.0.0.1:5433` (DB: `aiuthor_db`) |
| **Vite Frontend Dashboard** | Served statically at `/static/index.html` |
