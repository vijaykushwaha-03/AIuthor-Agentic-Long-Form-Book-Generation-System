# RAG Vector Retrieval Architecture

## Overview
This document describes the vector retrieval design and integration in the AIuthor backend.

---

## Database Requirements
* **Production/Local Setup**: PostgreSQL 16 + `pgvector` extension.
* **Fallback Policy**: 
  - SQLite is used for tests, utilizing the `JSON` column fallback.
  - PostgreSQL will **fail immediately** if pgvector is missing, unless explicitly permitted via `ALLOW_PGVECTOR_FALLBACK=true` in `.env`.

---

## Verification
To verify database readiness, run:
```powershell
python scripts/check_pgvector_embedding.py
```
This script audits:
- Database dialect and version.
- Registration of the `vector` extension.
- Column types of the `document_chunks` table.

---

## Semantic Retrieval
When performing vector similarity searches:
- If running on PostgreSQL with `pgvector` enabled, the system uses native cosine distance operators (`<=>` operator) and ranks results at the database level. In the response, `pgvector_used` will be set to `true`.
- If running on SQLite or fallback is allowed/active, the system performs Python-based ranking on fetched chunks, setting `pgvector_used` to `false`.
