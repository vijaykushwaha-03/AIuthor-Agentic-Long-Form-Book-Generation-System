# AIuthor Backend — Developer Reference

This directory contains the FastAPI backend code, database configurations, migrations, prompts, and testing suites.

## Project Progress Status

### Module 2.2 Completed (Core Book Tables)
- **BookProject** model added
- **BookRun** model added
- **Chapter** model added
- **BookSection** model added
- Alembic migration created and successfully run
- Core book tables migrated and verified

### Module 2.3A Completed (RAG Source Tables Without pgvector)
- **SourceDocument** model added
- **DocumentChunk** model added
- Alembic migration created and successfully run
- RAG source tables migrated and verified
- pgvector setup still postponed to Module 6

### Module 2.3B Completed (Memory Tables)
- **FactRegistry** model added
- **ConceptBible** model added
- **CharacterBible** model added
- **CallbackIndex** model added
- **ToneFingerprint** model added
- **DecisionLog** model added
- Alembic migration created and successfully run
- Memory tables migrated and verified

### Module 2.4A Completed (Observability Tables)
- **AgentTrace** model added
- **PromptLog** model added
- **MemoryIOLog** model added
- **TokenCostLedger** model added
- Alembic migration created and successfully run
- Observability tables migrated and verified

### Module 2.4B Completed (Eval + Export Tables)
- **EvalResult** model added
- **ExportFile** model added
- Alembic migration created and successfully run
- Eval/export tables migrated and verified

---

## Database Module Status

* **Module 2 Completion**: Module 2 has completed the database foundation.
* **Relational Tables**: All 18 relational tables are created and fully migrated.
* **Postponed pgvector**: In accordance with DEC-011, `pgvector` configuration and embedding columns are postponed to Module 6.
* **Next Phase**: Module 3 will introduce Pydantic schemas and API contracts.
* **Agent System**: No agent orchestrations or workflows exist yet.

### Useful Database & Test Commands

* **View Current Migration Revision**:
  ```powershell
  alembic current
  ```
* **Apply Outstanding Migrations**:
  ```powershell
  alembic upgrade head
  ```
* **Inspect Database Integrity & Tables**:
  ```powershell
  python scripts/check_db.py
  ```
* **Run Test Suites**:
  ```powershell
  pytest
  ```

---

## Database Migrations (Alembic)

Database schemas are versioned and managed using **Alembic**.

### How to Create a New Migration
Run this command from the `backend/` directory to generate a new migration script based on detection of changes in `app/models/`:
```powershell
alembic revision --autogenerate -m "description of changes"
```
The migration script is created under `backend/alembic/versions/`.

### How to Run Migrations
Apply all pending database migrations to the configured database:
```powershell
alembic upgrade head
```

### How to Rollback a Migration
Rollback the last migration:
```powershell
alembic downgrade -1
```

---

## Folder Structure

```
backend/
├── alembic/                # Migration environment and version files
│   ├── env.py              # Script run when Alembic env is invoked
│   ├── script.py.mako      # Template for migrations
│   └── versions/           # Folder containing migration revisions
├── app/
│   ├── api/                # FastAPI routing layers
│   ├── models/             # SQLAlchemy ORM models package
│   │   ├── __init__.py     # Module level declarations
│   │   └── base.py         # Custom types and common mixins (GUID, Timestamps)
│   ├── config.py           # Configuration management
│   ├── database.py         # Database engine and dependency session injections
│   └── main.py             # App instantiation and middleware
├── tests/                  # Test suite
└── alembic.ini             # Alembic system configuration settings
```
