# Memory API Contracts

This document describes the HTTP endpoints for persistent memory management (FactRegistry, ConceptBible, CharacterBible, CallbackIndex, ToneFingerprint, DecisionLog) and memory read/write envelope operations in the AIuthor backend.

> [!NOTE]
> **Module 4.2B Implemented**: All endpoints below are live.
> **No Memory Keeper Agent is implemented** in this module.
> **No automatic memory extraction** is implemented.
> These endpoints provide manual and API-level CRUD and envelope management. Agent-based memory writes and automatic extraction will be added in subsequent workflow modules.

---

## 1. Fact Registry Endpoints ✅ Implemented (Module 4.2B)

Fact registry stores factual claims and grounding evidence mapped to book projects and optionally chapters.

### 1.1 POST `/api/books/{book_id}/memory/facts`
* **Purpose**: Create a new fact claim linked to a book project.
* **Request Schema**: `FactRegistryCreate`
* **Response Schema**: `FactRegistryResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `book_id` is used as the source of truth. Raises `404` if the book or optional `chapter_id` does not exist.

### 1.2 GET `/api/books/{book_id}/memory/facts`
* **Purpose**: List facts for a book project (paginated, filtered status/chapter, sorted newest-first).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `status: str | None` — filter by fact status (e.g. `unverified`, `verified`, `retracted`)
  - `chapter_id: UUID | None` — filter by linked chapter
  - `search: str | None` — ILIKE match across the `claim` text
* **Response Schema**: `PaginatedResponse[FactRegistryResponse]`

### 1.3 GET `/api/books/{book_id}/memory/facts/{fact_id}`
* **Purpose**: Retrieve full details of a fact.
* **Response Schema**: `FactRegistryResponse`

### 1.4 PATCH `/api/books/{book_id}/memory/facts/{fact_id}`
* **Purpose**: Partial update of fact fields.
* **Request Schema**: `FactRegistryUpdate`
* **Response Schema**: `FactRegistryResponse`
* **Notes**: If `chapter_id` is updated, it verifies that the chapter exists for the book.

### 1.5 DELETE `/api/books/{book_id}/memory/facts/{fact_id}`
* **Purpose**: Permanently delete a fact claim.
* **Response Schema**: `MessageResponse`

---

## 2. Concept Bible Endpoints ✅ Implemented (Module 4.2B)

Concept bible stores recurring terminology, glossary candidates, and lore concepts.

### 2.1 POST `/api/books/{book_id}/memory/concepts`
* **Purpose**: Create a new concept definition.
* **Request Schema**: `ConceptBibleCreate`
* **Response Schema**: `ConceptBibleResponse`
* **Status Code**: `201 Created`
* **Notes**: Raises `409 Conflict` if the concept name already exists for the book.

### 2.2 GET `/api/books/{book_id}/memory/concepts`
* **Purpose**: List concepts for a book (paginated, sorted alphabetically by concept name).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `search: str | None` — ILIKE match across concept name and definition
* **Response Schema**: `PaginatedResponse[ConceptBibleResponse]`

### 2.3 GET `/api/books/{book_id}/memory/concepts/{concept_id}`
* **Purpose**: Retrieve concept details.
* **Response Schema**: `ConceptBibleResponse`

### 2.4 PATCH `/api/books/{book_id}/memory/concepts/{concept_id}`
* **Purpose**: Partial update of concept fields.
* **Request Schema**: `ConceptBibleUpdate`
* **Response Schema**: `ConceptBibleResponse`
* **Notes**: Raises `409 Conflict` if the concept name is updated to a concept that already exists for the book.

### 2.5 DELETE `/api/books/{book_id}/memory/concepts/{concept_id}`
* **Purpose**: Permanently delete a concept.
* **Response Schema**: `MessageResponse`

---

## 3. Character Bible Endpoints ✅ Implemented (Module 4.2B)

Character bible stores character details, traits, and arc summaries for story continuity.

### 3.1 POST `/api/books/{book_id}/memory/characters`
* **Purpose**: Create a new character continuity record.
* **Request Schema**: `CharacterBibleCreate`
* **Response Schema**: `CharacterBibleResponse`
* **Status Code**: `201 Created`
* **Notes**: Raises `409 Conflict` if character_name already exists for the book.

### 3.2 GET `/api/books/{book_id}/memory/characters`
* **Purpose**: List characters for a book (paginated, sorted alphabetically by character name).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `search: str | None` — ILIKE match across character_name, role, and arc_summary
* **Response Schema**: `PaginatedResponse[CharacterBibleResponse]`

### 3.3 GET `/api/books/{book_id}/memory/characters/{character_id}`
* **Purpose**: Retrieve character details.
* **Response Schema**: `CharacterBibleResponse`

### 3.4 PATCH `/api/books/{book_id}/memory/characters/{character_id}`
* **Purpose**: Partial update of character fields.
* **Request Schema**: `CharacterBibleUpdate`
* **Response Schema**: `CharacterBibleResponse`
* **Notes**: Raises `409 Conflict` if character_name is updated to one that already exists for the book.

### 3.5 DELETE `/api/books/{book_id}/memory/characters/{character_id}`
* **Purpose**: Permanently delete a character.
* **Response Schema**: `MessageResponse`

---

## 4. Callback Index Endpoints ✅ Implemented (Module 4.2B)

Callback index tracks references set up in earlier chapters that need to be revisited/called back in later chapters.

### 4.1 POST `/api/books/{book_id}/memory/callbacks`
* **Purpose**: Create a new callback reference.
* **Request Schema**: `CallbackIndexCreate`
* **Response Schema**: `CallbackIndexResponse`
* **Status Code**: `201 Created`

### 4.2 GET `/api/books/{book_id}/memory/callbacks`
* **Purpose**: List callbacks for a book (paginated, sorted by `source_chapter`, then `target_chapter`, then `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `status: str | None` — filter by status (e.g. `active`, `resolved`)
  - `source_chapter: int | None` — filter by source chapter number
  - `target_chapter: int | None` — filter by target chapter number
  - `search: str | None` — ILIKE match across concept name and callback text
* **Response Schema**: `PaginatedResponse[CallbackIndexResponse]`

### 4.3 GET `/api/books/{book_id}/memory/callbacks/{callback_id}`
* **Purpose**: Retrieve callback details.
* **Response Schema**: `CallbackIndexResponse`

### 4.4 PATCH `/api/books/{book_id}/memory/callbacks/{callback_id}`
* **Purpose**: Partial update of callback fields.
* **Request Schema**: `CallbackIndexUpdate`
* **Response Schema**: `CallbackIndexResponse`

### 4.5 DELETE `/api/books/{book_id}/memory/callbacks/{callback_id}`
* **Purpose**: Permanently delete a callback.
* **Response Schema**: `MessageResponse`

---

## 5. Tone Fingerprint Endpoints ✅ Implemented (Module 4.2B)

Tone fingerprint stores styling, rhythm, and lexical constraints used during book generation.

### 5.1 POST `/api/books/{book_id}/memory/tone-fingerprints`
* **Purpose**: Create a new tone fingerprint.
* **Request Schema**: `ToneFingerprintCreate`
* **Response Schema**: `ToneFingerprintResponse`
* **Status Code**: `201 Created`
* **Notes**: Standard `tone_name` enums (conversational, formal, poetic, etc.) are converted to lowercase strings.

### 5.2 GET `/api/books/{book_id}/memory/tone-fingerprints`
* **Purpose**: List tone fingerprints for a book (paginated, sorted newest-first).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `tone_name: str | None` — filter by tone name
* **Response Schema**: `PaginatedResponse[ToneFingerprintResponse]`

### 5.3 GET `/api/books/{book_id}/memory/tone-fingerprints/{tone_id}`
* **Purpose**: Retrieve tone fingerprint details.
* **Response Schema**: `ToneFingerprintResponse`

### 5.4 PATCH `/api/books/{book_id}/memory/tone-fingerprints/{tone_id}`
* **Purpose**: Partial update of tone fingerprint fields.
* **Request Schema**: `ToneFingerprintUpdate`
* **Response Schema**: `ToneFingerprintResponse`

### 5.5 DELETE `/api/books/{book_id}/memory/tone-fingerprints/{tone_id}`
* **Purpose**: Permanently delete a tone fingerprint.
* **Response Schema**: `MessageResponse`

---

## 6. Decision Log Endpoints ✅ Implemented (Module 4.2B)

Decision log tracks key architecture and engineering decisions. Decisions can be linked to a book project or remain global.

### 6.1 POST `/api/books/{book_id}/memory/decisions`
* **Purpose**: Log a decision linked to a book project.
* **Request Schema**: `DecisionLogCreate`
* **Response Schema**: `DecisionLogResponse`
* **Status Code**: `201 Created`

### 6.2 GET `/api/books/{book_id}/memory/decisions`
* **Purpose**: List decisions for a book project (paginated, sorted newest-first).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `search: str | None` — ILIKE match across decision, reason, and impact
* **Response Schema**: `PaginatedResponse[DecisionLogResponse]`

### 6.3 GET `/api/books/{book_id}/memory/decisions/{decision_id}`
* **Purpose**: Retrieve details of a book-scoped decision.
* **Response Schema**: `DecisionLogResponse`
* **Notes**: Raises `404` if decision belongs to a different book or does not exist.

### 6.4 PATCH `/api/books/{book_id}/memory/decisions/{decision_id}`
* **Purpose**: Partial update of book-scoped decision fields.
* **Request Schema**: `DecisionLogUpdate`
* **Response Schema**: `DecisionLogResponse`

### 6.5 DELETE `/api/books/{book_id}/memory/decisions/{decision_id}`
* **Purpose**: Permanently delete a book-scoped decision.
* **Response Schema**: `MessageResponse`

### 6.6 GET `/api/memory/decisions`
* **Purpose**: List all decisions globally (including those not linked to a book).
* **Query Parameters**:
  - `book_id: UUID | None` — optional filter by book project
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `search: str | None` — ILIKE match across decision, reason, and impact
* **Response Schema**: `PaginatedResponse[DecisionLogResponse]`

---

## 7. Memory Envelope Endpoints ✅ Implemented (Module 4.2B)

Memory envelope endpoints provide batch operations for reading and writing different memory categories in a single request.

### 7.1 POST `/api/books/{book_id}/memory/read`
* **Purpose**: Batch read multiple memory groups.
* **Request Schema**: `MemoryReadRequest`
* **Response Schema**: `MemoryReadResponse`
* **Status Code**: `200 OK`
* **Notes**:
  - If `memory_types` is not specified, returns all 6 groups.
  - If `chapter_number` is provided, facts are filtered by `used_in_chapters` and callbacks are filtered by `source_chapter`/`target_chapter`.
  - If `query` is provided, applies lexical search across text fields.

### 7.2 POST `/api/books/{book_id}/memory/write`
* **Purpose**: Batch write multiple memory groups.
* **Request Schema**: `MemoryWriteRequest`
* **Response Schema**: `MemoryWriteResponse`
* **Status Code**: `200 OK`
* **Notes**:
  - Validates consistency of `book_id` for all items against the request path. Raises `400 Bad Request` if mismatch detected.
  - Returns count of created records for each memory category.
