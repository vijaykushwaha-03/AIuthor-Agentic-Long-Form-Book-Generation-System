# RAG API Contracts

This document describes the HTTP endpoints for source document management, document chunking, and retrieval in the AIuthor backend.

> [!NOTE]
> **Module 4.2A Implemented**: All endpoints below are live.
> **No embeddings, no pgvector, no vector columns** are used in this module.
> Real semantic vector retrieval is deferred to **Module 6**.

---

## 1. Source Document Endpoints ✅ Implemented (Module 4.2A)

Source documents are raw reference materials (papers, web pages, uploaded files) that are chunked and optionally indexed for RAG retrieval.

### 1.1 POST `/api/books/{book_id}/sources`
* **Purpose**: Create a new source document linked to a book project.
* **Request Schema**: `SourceDocumentCreate`
* **Response Schema**: `SourceDocumentResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `book_id` is used as the source of truth. Raises `404` if book does not exist.

### 1.2 GET `/api/books/{book_id}/sources`
* **Purpose**: List source documents for a book (paginated, filtered, sorted newest-first).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 20` (max 100)
  - `status: str | None` — filter by document status (e.g. `created`, `parsed`, `indexed`)
  - `source_type: str | None` — filter by type (e.g. `paper`, `web`, `upload`)
  - `search: str | None` — ILIKE match across title, source_url, raw_text
* **Response Schema**: `PaginatedResponse[SourceDocumentListItem]`

### 1.3 GET `/api/books/{book_id}/sources/{document_id}`
* **Purpose**: Retrieve full detail of a source document (including raw_text).
* **Response Schema**: `SourceDocumentResponse`

### 1.4 PATCH `/api/books/{book_id}/sources/{document_id}`
* **Purpose**: Partial update of source document fields (title, raw_text, metadata, status, etc.).
* **Request Schema**: `SourceDocumentUpdate`
* **Response Schema**: `SourceDocumentResponse`

### 1.5 DELETE `/api/books/{book_id}/sources/{document_id}`
* **Purpose**: Permanently delete a source document. Cascades to all associated `DocumentChunk` records.
* **Response Schema**: `MessageResponse`

### 1.6 PATCH `/api/sources/{document_id}/status`
* **Purpose**: Update a source document's pipeline status independently of book context.
* **Request Body**:
  ```json
  { "status": "parsed" }
  ```
* **Response Schema**: `SourceDocumentResponse`
* **Typical status values**: `created → parsed → chunked → indexed`

---

## 2. Document Chunk Endpoints ✅ Implemented (Module 4.2A)

Document chunks are segments of source document text prepared for retrieval.

> [!IMPORTANT]
> `DocumentChunk` has an `embedding_status` field and `embedding_model` field for metadata tracking.
> **No vector data is stored** — the `embedding` column does not exist in this module.
> All chunks are created with `embedding_status = "pending"` until Module 6 generates real vectors.

### 2.1 POST `/api/sources/{document_id}/chunks`
* **Purpose**: Manually create a single chunk record.
* **Request Schema**: `DocumentChunkCreate`
* **Response Schema**: `DocumentChunkResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `document_id` is used as the source of truth. Raises `409 Conflict` on duplicate `chunk_index`.

### 2.2 GET `/api/sources/{document_id}/chunks`
* **Purpose**: List all chunks for a document (sorted by `chunk_index` ascending).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `embedding_status: str | None` — filter by status (e.g. `pending`, `completed`)
  - `search: str | None` — ILIKE match across chunk_text
* **Response Schema**: `PaginatedResponse[DocumentChunkListItem]`

### 2.3 GET `/api/sources/{document_id}/chunks/{chunk_id}`
* **Purpose**: Retrieve full detail of a single chunk.
* **Response Schema**: `DocumentChunkResponse`

### 2.4 PATCH `/api/sources/{document_id}/chunks/{chunk_id}`
* **Purpose**: Partial update of a chunk's text, token_count, or metadata.
* **Request Schema**: `DocumentChunkUpdate`
* **Response Schema**: `DocumentChunkResponse`
* **Notes**: Does NOT update vector fields (no vector fields exist yet).

### 2.5 DELETE `/api/sources/{document_id}/chunks/{chunk_id}`
* **Purpose**: Permanently delete a chunk.
* **Response Schema**: `MessageResponse`

### 2.6 PATCH `/api/chunks/{chunk_id}/embedding-status`
* **Purpose**: Update a chunk's `embedding_status` and optionally its `embedding_model`.
* **Request Body**:
  ```json
  {
    "embedding_status": "completed",
    "embedding_model": "text-embedding-3-small"
  }
  ```
* **Response Schema**: `DocumentChunkResponse`

> [!WARNING]
> This endpoint updates metadata only. It does **NOT** store a vector embedding.
> Real vector storage will be added in Module 6 (pgvector extension).

---

## 3. Utility Endpoints ✅ Implemented (Module 4.2A)

### 3.1 POST `/api/sources/{document_id}/chunk`
* **Purpose**: Split a source document's `raw_text` into `DocumentChunk` records.
* **Request Schema**: `ChunkingRequest`
* **Response Schema**: `ChunkingResponse`
* **Algorithm**: Simple deterministic character-window splitter.
  - Slides a window of `chunk_size` characters with a step of `chunk_size - chunk_overlap`.
  - Accepts `strategy` field but applies the same splitter regardless.
  - Appends chunks after the current max `chunk_index` (supports incremental re-chunking).
  - Sets `token_count` using approximate word count.
* **All chunks created with** `embedding_status = "pending"`.

> [!NOTE]
> This is a **local-only** operation. No LLM, no embeddings, no external services.
> Future modules will support smarter splitters (sentence, paragraph, recursive) and automatic embedding triggers.

### 3.2 POST `/api/rag/retrieve`
* **Purpose**: Keyword search over stored chunk text (placeholder for future vector search).
* **Request Schema**: `RetrievalRequest`
* **Response Schema**: `RetrievalResponse`
* **Algorithm**: `ILIKE` SQL keyword search on `chunk_text`.
  - Scores all matches as `1.0` (flat — no ranking).
  - Respects `top_k` limit.
  - Filters by `book_id` if provided.
  - Returns `include_raw_text` controlled chunk text.

> [!CAUTION]
> **This is a lexical placeholder only.** Results are keyword matches, not semantic matches.
> No embeddings, no pgvector, no cosine similarity are used.
> **Real semantic vector retrieval will be implemented in Module 6.**

---

## 4. Data Model Notes

| Field | Where | Notes |
|-------|-------|-------|
| `status` | `SourceDocument` | `created → parsed → chunked → indexed` |
| `embedding_status` | `DocumentChunk` | `pending → queued → completed → failed` |
| `embedding_model` | `DocumentChunk` | Model name string, metadata only |
| `chunk_index` | `DocumentChunk` | Unique per document (enforced by DB constraint) |
| `book_id` | Both | Optional; inherited from parent document when not set |

**No vector column exists** in `DocumentChunk`. The `pgvector` extension and `embedding` column will be added in Module 6 without breaking existing records.

---

## 5. Module 6.1 — Hybrid Retrieval & Context Pack Endpoints ✅ Implemented (Module 6.1)

These endpoints implement advanced hybrid search (merging vector similarity and term-based overlap) and structured context packing for LLM agents.

### 5.1 POST `/api/rag/hybrid-retrieve`
* **Purpose**: Hybrid lexical + semantic retrieval.
* **Request Schema**: `HybridRetrievalRequest`
* **Response Schema**: `HybridRetrievalResponse`
* **Status Code**: `200 OK`
* **Algorithm**:
  - Semantic retrieve is run with `top_k = request.top_k * 2`.
  - Lexical retrieve is run with case-insensitive `LIKE` matching, scoring exact phrases as `1.0` and term overlaps as `count(matched) / total_terms`.
  - Scores are merged using: `score = semantic_score * semantic_weight + lexical_score * lexical_weight` (missing mode score = 0).
  - Results are sorted by score descending, breaking ties by `chunk_index` ascending.
  - Final results are capped at `top_k` and given sequential citation IDs `C1, C2, C3...`.

### 5.2 POST `/api/rag/context-pack`
* **Purpose**: Construct agent-ready RAG context pack.
* **Request Schema**: `ContextPackRequest`
* **Response Schema**: `ContextPackResponse`
* **Status Code**: `200 OK`
* **Behavior**:
  - Validates `book_id` and `chapter_id`.
  - Runs hybrid retrieval and converts matches to `ContextChunk` list.
  - Groups and concatenates chunk text in a stable, agent-readable format:
    ```
    [C1] Source: <source_title or document_id>, Chunk <chunk_index>
    <chunk_text>
    ```
  - Enforces character constraints (`max_context_chars`), truncating the first chunk if it exceeds the limit, and stopping cleanly otherwise.

