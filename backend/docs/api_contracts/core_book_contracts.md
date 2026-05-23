# Core Book API Contracts

This document documents the HTTP endpoints for book project management, run monitoring, chapter generation, and front/back matter sections in the AIuthor backend.

> [!NOTE]
> **Module 4.1A + 4.1B Implemented**: All endpoints in Sections 1–4 are now live.
> RAG, memory, observability, eval, and export routes will be documented in later modules.

---

## 1. Book Project Endpoints ✅ Implemented (Module 4.1A)

### 1.1 POST `/api/books`
* **Purpose**: Create a new book project from a user-supplied brief.
* **Request Schema**: `BookProjectCreate`
* **Response Schema**: `BookProjectResponse`
* **Status**: `201 Created`

### 1.2 GET `/api/books`
* **Purpose**: List book projects with pagination, filtering, and sorting.
* **Query Parameters**: `page`, `page_size`, `status`, `tone`, `genre`, `search`, `sort_by`, `sort_order`
* **Response Schema**: `PaginatedResponse[BookProjectListItem]`

### 1.3 GET `/api/books/{book_id}`
* **Purpose**: Retrieve detailed metadata and current status for a single book project.
* **Response Schema**: `BookProjectResponse`

### 1.4 PATCH `/api/books/{book_id}`
* **Purpose**: Partial update of a book project's metadata or status.
* **Request Schema**: `BookProjectUpdate`
* **Response Schema**: `BookProjectResponse`

### 1.5 DELETE `/api/books/{book_id}`
* **Purpose**: Permanently delete a book project (cascades to all related data).
* **Response Schema**: `MessageResponse`

---

## 2. Book Run Endpoints ✅ Implemented (Module 4.1A)

### 2.1 POST `/api/books/{book_id}/runs`
* **Purpose**: Create a new pending run for a book project.
* **Response Schema**: `BookRunResponse`
* **Status**: `201 Created`

### 2.2 GET `/api/books/{book_id}/runs`
* **Purpose**: List all runs for a book (paginated, optional status filter).
* **Response Schema**: `PaginatedResponse[BookRunResponse]`

### 2.3 GET `/api/runs/{run_id}`
* **Purpose**: Retrieve details of a specific execution run.
* **Response Schema**: `BookRunResponse`

### 2.4 PATCH `/api/runs/{run_id}`
* **Purpose**: Partial update of a run's state or metadata.
* **Request Schema**: `BookRunUpdate`
* **Response Schema**: `BookRunResponse`

### 2.5 GET `/api/runs/{run_id}/status`
* **Purpose**: Get monitoring envelope with `progress_percentage` and `message`.
* **Response Schema**: `BookRunStatusResponse`

### 2.6 POST `/api/runs/{run_id}/start`
* **Purpose**: Transition run → `running`. Sets `started_at`.
* **Response Schema**: `BookRunResponse`

### 2.7 POST `/api/runs/{run_id}/complete`
* **Purpose**: Transition run → `completed`. Sets `completed_at`.
* **Response Schema**: `BookRunResponse`

### 2.8 POST `/api/runs/{run_id}/fail`
* **Purpose**: Transition run → `failed`. Sets `completed_at` and `error_message`.
* **Request Body**: `{ "error_message": "..." }`
* **Response Schema**: `BookRunResponse`

---

## 3. Chapter Endpoints ✅ Implemented (Module 4.1B)

### 3.1 POST `/api/books/{book_id}/chapters`
* **Purpose**: Create a chapter record for a book.
* **Request Schema**: `ChapterCreate`
* **Response Schema**: `ChapterResponse`
* **Status**: `201 Created`
* **Note**: Raises `409 Conflict` if `chapter_number` already exists for the book.

### 3.2 GET `/api/books/{book_id}/chapters`
* **Purpose**: List chapters sorted by `chapter_number` ascending.
* **Query Parameters**: `page`, `page_size`, `status`, `tone`, `search`
* **Response Schema**: `PaginatedResponse[ChapterListItem]`

### 3.3 GET `/api/books/{book_id}/chapters/{chapter_id}`
* **Purpose**: Retrieve full detail (all text versions, contract, status) of a chapter.
* **Response Schema**: `ChapterResponse`

### 3.4 PATCH `/api/books/{book_id}/chapters/{chapter_id}`
* **Purpose**: Partial update of chapter content, metadata, or status.
* **Request Schema**: `ChapterUpdate`
* **Response Schema**: `ChapterResponse`

### 3.5 DELETE `/api/books/{book_id}/chapters/{chapter_id}`
* **Purpose**: Permanently delete a chapter.
* **Response Schema**: `MessageResponse`

### 3.6 POST `/api/books/{book_id}/chapters/insert`
* **Purpose**: Insert a new chapter after a specific position; shifts existing chapters.
* **Request Schema**: `ChapterInsertRequest`
* **Response Schema**: `ChapterResponse`
* **Status**: `201 Created`
* **Current Behaviour**: Shifts existing chapter numbers by +1 at the insertion point.
  Sets `chapter_contract.repair_required = true` and `chapter_contract.inserted = true`.
  **Does NOT run real TOC/callback/glossary repair** — that is deferred to a later
  workflow module. Routes consumers can detect `repair_required` and trigger repair later.
* **Future Behaviour**: Will invoke Test D's full repair flow (TOC regeneration, callback
  realignment, glossary term appending).

### 3.7 POST `/api/books/{book_id}/chapters/reorder`
* **Purpose**: Reassign `chapter_number` sequentially (1, 2, 3, …). Useful after deletions.
* **Response Schema**: `list[ChapterListItem]`

---

## 4. Book Section (Front/Back Matter) Endpoints ✅ Implemented (Module 4.1B)

### 4.1 POST `/api/books/{book_id}/sections`
* **Purpose**: Create a front or back matter section.
* **Request Schema**: `BookSectionCreate`
* **Response Schema**: `BookSectionResponse`
* **Status**: `201 Created`

### 4.2 GET `/api/books/{book_id}/sections`
* **Purpose**: List all sections sorted by `sort_order` then `created_at`.
* **Query Parameters**: `section_type`, `status`
* **Response Schema**: `list[BookSectionListItem]`

### 4.3 GET `/api/books/{book_id}/sections/{section_id}`
* **Purpose**: Retrieve full detail of a specific section.
* **Response Schema**: `BookSectionResponse`

### 4.4 PATCH `/api/books/{book_id}/sections/{section_id}`
* **Purpose**: Partial update of a section's content, title, or status.
* **Request Schema**: `BookSectionUpdate`
* **Response Schema**: `BookSectionResponse`

### 4.5 DELETE `/api/books/{book_id}/sections/{section_id}`
* **Purpose**: Permanently delete a section.
* **Response Schema**: `MessageResponse`

### 4.6 POST `/api/books/{book_id}/sections/defaults`
* **Purpose**: Create missing required front matter and back matter sections.
  Idempotent — existing `section_type` values are not duplicated.
* **Front matter** (`sort_order` 0–9): `half_title`, `title_page`, `copyright`, `dedication`,
  `epigraph`, `toc`, `foreword`, `preface`, `acknowledgments`, `introduction`
* **Back matter** (`sort_order` 1000–1005): `afterword`, `appendix`, `glossary`,
  `references`, `about_author`, `back_cover_copy`
* **Response Schema**: `list[BookSectionListItem]`

### 4.7 POST `/api/books/{book_id}/sections/reorder`
* **Purpose**: Reassign `sort_order` sequentially (0, 1, 2, …). Useful after deletions.
* **Response Schema**: `list[BookSectionListItem]`
