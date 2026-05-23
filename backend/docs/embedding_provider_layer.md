# Embedding Provider Layer — Module 6.0A

## Overview

Module 6.0A introduces a clean, provider-agnostic embedding abstraction layer.
It prepares the backend for semantic RAG (Module 6.0B+) without implementing
chunk embedding jobs or vector search yet.

---

## Supported Providers

| Provider | Identifier | Default |
|----------|-----------|---------|
| Google Gemini | `gemini` | ✅ Yes |
| OpenAI | `openai` | No |
| Mock (tests/dev) | `mock` | No |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `gemini` | Active provider: `gemini`, `openai`, or `mock` |
| `GEMINI_EMBEDDING_MODEL` | `text-embedding-004` | Gemini embedding model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OPENAI_EMBEDDING_DIMENSIONS` | `1536` | Output dimensions for OpenAI model |
| `EMBEDDING_DIMENSIONS` | `768` | Default vector dimensions (Gemini-oriented) |
| `EMBEDDING_BATCH_SIZE` | `32` | Texts per batch (used in Module 6.0B job) |

---

## Usage Examples

### Gemini Embeddings (default)

```dotenv
# backend/.env
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
GEMINI_EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSIONS=768
```

```python
from app.services.embedding_service import EmbeddingService
from app.embeddings.schemas import EmbeddingRequest

service = EmbeddingService()  # reads EMBEDDING_PROVIDER=gemini from env

request = EmbeddingRequest(texts=[
    "Chapter 1: The hero begins their journey.",
    "Chapter 2: The first obstacle appears.",
])

response = service.embed_texts(request)
print(response.dimensions)          # 768
print(len(response.items))          # 2
print(response.items[0].embedding)  # [0.031, -0.142, ...]
```

### OpenAI Embeddings

```dotenv
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536
```

No code changes needed — the factory resolves the provider automatically.

### Mock Embeddings (tests / offline dev)

```dotenv
EMBEDDING_PROVIDER=mock
EMBEDDING_DIMENSIONS=8
```

```python
from app.embeddings.providers import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService
from app.embeddings.schemas import EmbeddingRequest

service = EmbeddingService(provider=MockEmbeddingProvider(dims=8))

request = EmbeddingRequest(texts=["Hello world."])
response = service.embed_texts(request)
# response.items[0].embedding == [deterministic 8-float vector]
```

### Factory direct usage

```python
from app.embeddings.factory import get_embedding_provider

provider = get_embedding_provider("mock")    # explicit override
provider = get_embedding_provider()          # uses EMBEDDING_PROVIDER env var
```

---

## API Endpoints

### `GET /api/embeddings/provider`

Returns the current embedding provider configuration. **No embedding call is made.**

```json
{
  "provider": "gemini",
  "model": "text-embedding-004",
  "dimensions": 768,
  "configured": true,
  "supports_batching": true
}
```

### `POST /api/embeddings/mock`

Always uses `MockEmbeddingProvider`. Use to verify the API contract without any real API calls.

**Request:**
```json
{
  "texts": ["Chapter one begins with a dark night.", "The hero stirs."]
}
```

**Response:**
```json
{
  "provider": "mock",
  "model": "mock-embedding",
  "dimensions": 8,
  "items": [
    {"text_index": 0, "embedding": [0.12, -0.34, ...], "token_count": 7},
    {"text_index": 1, "embedding": [0.45, 0.23, ...],  "token_count": 3}
  ]
}
```

---

## Architecture

```
app/embeddings/
├── __init__.py     ← public re-exports
├── schemas.py      ← EmbeddingRequest, EmbeddingItem, EmbeddingResponse, EmbeddingProviderInfo
├── exceptions.py   ← EmbeddingError, EmbeddingConfigurationError, EmbeddingProviderError
├── base.py         ← BaseEmbeddingProvider (abstract)
├── providers.py    ← MockEmbeddingProvider, GeminiEmbeddingProvider, OpenAIEmbeddingProvider
└── factory.py      ← get_embedding_provider(), get_default_embedding_provider()

app/services/
└── embedding_service.py  ← EmbeddingService wrapper

app/api/
└── routes_embeddings.py  ← GET /api/embeddings/provider, POST /api/embeddings/mock

app/db/
├── __init__.py
└── pgvector_check.py     ← is_pgvector_available(), get_pgvector_status()
```

---

## pgvector Readiness

The `app/db/pgvector_check.py` module provides two read-only utility functions:

```python
from app.db.pgvector_check import is_pgvector_available, get_pgvector_status

available: bool = is_pgvector_available(db)

status = get_pgvector_status(db)
# {
#   "available": True | False,
#   "extension_name": "vector",
#   "message": "..."
# }
```

**These functions are safe to call against SQLite (test) databases — they return False without raising.**

To install pgvector in PostgreSQL:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The Alembic migration to add this will be created in **Module 6.0B**.

---

## Design Decisions

### Lazy SDK client creation

SDK clients are created inside `embed()`, not `__init__`. This means:
- Providers can be imported and inspected in tests without network access.
- `GeminiEmbeddingProvider(api_key="fake")` works in tests as long as `.embed()` is not called.

### Deterministic mock vectors

`MockEmbeddingProvider` uses SHA-256 hashing to produce L2-normalised float vectors:
- Same text → same vector (reproducible).
- Different texts → (almost always) different vectors.
- No external calls, no randomness.

### Dimensions flexibility

Embedding dimensions are configurable per request via `EmbeddingRequest.dimensions`.
For providers that do not support custom dimensions, the actual vector length is used.

---

## Important Notes

- **No chunk embedding job yet.** Stored `DocumentChunk` rows will be embedded in Module 6.0B.
- **No semantic retrieval yet.** Vector similarity search comes in Module 6.0B.
- **No vector column migration.** The `embedding` column on `DocumentChunk` is added in Module 6.0B.
- **Tests use mock only.** All tests pass offline with no API keys.
- **No database migrations.** This module adds no new Alembic migrations.
- **No agents or LangGraph.** Not part of this module.
