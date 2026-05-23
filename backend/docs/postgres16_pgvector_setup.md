# PostgreSQL 16 + pgvector Setup Reference

## Why PostgreSQL 16 is Used
* **PostgreSQL 18 Compatibility**: Local setups for PostgreSQL 18 ran into compilation and library dependency limitations on Windows when installing the `pgvector` extension.
* **Stable Selection**: PostgreSQL 16 + `pgvector` v0.8.2 was chosen as the active database configuration for local development.

---

## Required PostgreSQL Setup

Ensure that the database is running and `pgvector` is registered:

1. **Enable pgvector**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Verify PostgreSQL Version**:
   ```sql
   SELECT version();
   ```

3. **Verify pgvector Registration & Version**:
   ```sql
   SELECT extname, extversion
   FROM pg_extension
   WHERE extname = 'vector';
   ```

4. **Verify Embedding Column Type**:
   Inspect that the `embedding` column on the `document_chunks` table is natively defined as a `vector(768)` type:
   ```sql
   SELECT
       a.attname,
       format_type(a.atttypid, a.atttypmod) AS column_type
   FROM pg_attribute a
   JOIN pg_class c ON a.attrelid = c.oid
   WHERE c.relname = 'document_chunks'
     AND a.attname = 'embedding'
     AND a.attnum > 0
     AND NOT a.attisdropped;
   ```
   *Expected type:* `vector(768)` or `USER-DEFINED` representing `vector`.

---

## Local Verification Commands

Run the following commands inside the `backend/` directory to sync and verify your database environment:

```powershell
# Apply Alembic schema migrations (includes table creations & HNSW indexes)
alembic upgrade head

# Run database schema completeness check (verifies all 18 tables & types)
python scripts/check_pgvector_embedding.py

# Execute the test suite
pytest
```

---

## Environment Variable Configuration

* **`DATABASE_URL`**: Must point to your PostgreSQL 16 instance.
  ```ini
  DATABASE_URL=postgresql+psycopg2://aiuthor:aiuthor_secret@127.0.0.1:5433/aiuthor_db
  ```
* **`GEMINI_API_KEY`**: Required for real embedding generation via Gemini API.
* **Mock Provider**: Automated tests will automatically configure and use the mock embedding provider to avoid making network requests or requiring API keys.

---

## Fallback Policies

* **SQLite / Local Tests**: Uses the `JSON` column type fallback for vector embeddings (configured dynamically using SQLAlchemy `.with_variant(JSON, "sqlite")`).
* **PostgreSQL Production / Dev**: Expects a true `vector(768)` data type.
* **Fallbacks**: If the connected database is PostgreSQL but `pgvector` is not enabled, the system will **fail immediately** with a `ServiceError` unless `ALLOW_PGVECTOR_FALLBACK=true` is set in your `.env`.
