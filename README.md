# AIuthor — Agentic Long-Form Book Generation System

AIuthor is a production-style agentic system that generates publication-ready books from a user brief. It uses separate agents (Planner, Researcher, Writer, Humanizer, Editor, Fact Checker, Memory Keeper, Assembler) orchestrated via LangGraph, with PostgreSQL + pgvector for persistent memory and RAG, and DOCX/PDF export.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Pydantic v2 |
| Database | PostgreSQL 18 (local) + pgvector |
| Orchestration | LangGraph |
| Exports | python-docx + LibreOffice |
| Frontend | React + Vite + Tailwind (later) |
| Testing | Pytest + Playwright |

---

## Prerequisites

- Python 3.11+
- PostgreSQL 18 installed and running locally
- Git

---

## Local Setup (No Docker)

### 1. Clone the repository
```bash
git clone <repo-url>
cd AIuthor-Agentic-Long-Form-Book-Generation-System
```

### 2. PostgreSQL Setup

#### 2a. Make sure PostgreSQL is running
```powershell
Get-Service postgresql-x64-18
# Should show: Running
```

#### 2b. Create the database user and database
Open a terminal as Administrator (or use pgAdmin), then run:
```sql
-- Connect as postgres superuser
-- In psql: psql -U postgres -h 127.0.0.1

CREATE USER aiuthor WITH PASSWORD 'aiuthor_secret' CREATEDB;
CREATE DATABASE aiuthor_db OWNER aiuthor;
```

#### 2c. Add PostgreSQL to PATH (PowerShell — current session)
```powershell
$env:PATH += ";C:\Program Files\PostgreSQL\18\bin"
```

To make this permanent, add `C:\Program Files\PostgreSQL\18\bin` to your System Environment Variables.

#### 2d. Verify connection
```bash
psql -U aiuthor -h 127.0.0.1 -d aiuthor_db -c "SELECT version();"
# Should print: PostgreSQL 18.3 on x86_64-windows ...
```

### 3. Python Virtual Environment
```powershell
cd backend
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Command Prompt)
.\.venv\Scripts\activate.bat
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Environment
```powershell
copy .env.example .env
# .env is already pre-filled for local Postgres
# Edit if your credentials differ
```

The default `.env` settings:
```
DATABASE_URL=postgresql+psycopg2://aiuthor:aiuthor_secret@127.0.0.1:5432/aiuthor_db
APP_ENV=development
APP_VERSION=0.1.0
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 6. Run the Backend Server
```powershell
# From backend/ directory with venv activated
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Server starts at: **http://127.0.0.1:8000**

You should see:
```
INFO: Database ping successful.
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## API Endpoints (Module 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check (load-balancer probe) |
| GET | `/api/version` | API version and service name |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/redoc` | ReDoc documentation |

### Example responses
```bash
# Health check
curl http://127.0.0.1:8000/health
# {"status":"ok","env":"development","version":"0.1.0"}

# Version
curl http://127.0.0.1:8000/api/version
# {"version":"0.1.0","service":"aiuthor-backend"}
```

---

## Running Tests

Tests use in-memory SQLite — **no Postgres needed** to run the test suite.

```powershell
# From backend/ directory with venv activated
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

Expected output:
```
15 passed in 0.21s
```

---

## Project Structure

```
AIuthor-Agentic-Long-Form-Book-Generation-System/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory (create_app)
│   │   ├── config.py            # Pydantic Settings — reads from .env
│   │   ├── database.py          # Lazy SQLAlchemy engine + get_db() dep
│   │   └── api/
│   │       └── routes_health.py # GET /health  GET /api/version
│   ├── prompts/                 # Agent prompt markdown files (Module 4)
│   ├── tests/
│   │   ├── conftest.py          # Fixtures (SQLite override for tests)
│   │   └── test_health.py       # 15 tests
│   ├── .env                     # Your local config (git-ignored)
│   ├── .env.example             # Template with all variables
│   ├── requirements.txt
│   └── pyproject.toml           # Pytest config
├── docs/
│   └── decisions.md             # 10 engineering decisions
├── docker-compose.yml           # Optional: Docker setup (not required)
└── README.md
```

---

## Credentials Summary

| What | Value |
|------|-------|
| Postgres host | 127.0.0.1:5432 |
| DB name | aiuthor_db |
| DB user | aiuthor |
| DB password | aiuthor_secret |
| Postgres superuser | postgres / aiuthor_pg_2026 |
| API base URL | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |

---

## Implementation Modules

| Module | Status | Description |
|--------|--------|-------------|
| 0 | ✅ Done | Repository foundation, structure, config |
| 1 | ✅ Done | FastAPI core, health endpoints, DB session |
| 2 | ⏳ Next | SQLAlchemy models + Alembic migrations |
| 3 | ⏳ | Pydantic schemas for agent I/O |
| 4 | ⏳ | Prompt registry |
| 5 | ⏳ | Observability (traces, prompt logs, token ledger) |
| 6 | ⏳ | RAG pipeline + pgvector |
| 7 | ⏳ | Memory system |
| 8 | ⏳ | LangGraph orchestration |
| 9 | ⏳ | Agent implementations |
| 10 | ⏳ | Chapter insertion repair |
| 11 | ⏳ | DOCX/PDF export |
| 12 | ⏳ | Evals |
