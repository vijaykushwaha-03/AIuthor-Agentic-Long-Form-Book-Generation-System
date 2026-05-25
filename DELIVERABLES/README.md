# AIuthor — Submission Delivery Brief

This folder contains the complete, production-grade mandatory deliverables for the **AIuthor Agentic Long-Form Book Generation System** technical assessment.

## 📁 Delivery Mapping Checklist

| Required Deliverable | File / Location | Description |
| :--- | :--- | :--- |
| **1. Prompts Dossier** | [PROMPTS_DOSSIER.md](PROMPTS_DOSSIER.md) | Standardized dossier documenting all 8 agent templates, versions, input/output schemas, safety rules, and failure modes. |
| **2. Working MVP** | [docker-compose.yml](../docker-compose.yml) | One-command runnable setup utilizing Docker Compose. Starts the FastAPI backend, PostgreSQL, pgvector, and Redis cache. |
| **3. Source Repo** | Direct Git History | Honest commit history and codebase structure. |
| **4. Architecture Doc** | [ARCHITECTURE.md](ARCHITECTURE.md) | documents the LangGraph agent topology, data flow, memory architecture, and failure mitigation loops. |
| **5. Memory Schema** | [MEMORY_SCHEMA.md](MEMORY_SCHEMA.md) | Detailed schema descriptions of all transactional and continuity databases with real concrete example records. |
| **6. Evals Report** | [EVALS_REPORT.md](EVALS_REPORT.md) | Programmatic scorecard scoring the generated book for structures, callback integrity, AI tells, and fact grounding. |
| **7. Trace Bundle** | [TRACE_SUMMARY.md](TRACE_SUMMARY.md) & [MANIFEST.json](MANIFEST.json) | Full execution trace, token ledgers, prompt logs, and billing costs compiled for the RAG test run. |
| **8. Sample Books** | [sample_books/](sample_books/) | Generated manuscript files in DOCX format (TOC, front matter, body chapters, glossary, bibliography). |
| **9. Demo Video** | Local File / Loom Link | A 5–8 minute video detailing the UI dashboard and multi-agent loops. |
| **10. Design Decisions** | [DESIGN_DECISIONS_LOG.md](DESIGN_DECISIONS_LOG.md) | Engineering Decisions Log documenting the 11 key structural design trade-offs made. |

---

## 🚀 Running the MVP

### Prerequisites
- Docker & Docker Compose
- Gemini API Key / OpenAI API Key (configured in `.env`)

### Startup Command
Run the following command in the root directory to spin up the database, vector store, and FastAPI server:
```bash
docker compose up --build
```
The application will boot up:
- **API Swagger documentation**: `http://localhost:8000/docs`
- **Frontend App**: `http://localhost:5173/`

To launch an automated dry run or test case runner:
```bash
# Set up a python virtual env
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run the backend locally
uvicorn app.main:app --port 8000
```
Use the Swagger UI at `http://localhost:8000/docs` to trigger Scenario run executions.
