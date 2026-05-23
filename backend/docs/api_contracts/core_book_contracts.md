# Core Book API Contracts Preview

This document previews the planned HTTP endpoints for book project management, run monitoring, chapter generation, and front/back matter sections in the AIuthor backend.

> [!NOTE]
> **Implementation Status**: This is a preview reference for future routes. Actual endpoints will be implemented in subsequent modules. No active route execution or agent orchestration occurs in these schema definition modules.
> 
> RAG, memory, observability, eval, and export routes will be documented later. Current documents focus on core book contracts. Actual routes are not yet implemented.

---

## 1. Book Project Endpoints

### 1.1 POST `/api/books`
* **Purpose**: Create a new book project from a user-supplied brief.
* **Request Schema**: `BookProjectCreate`
* **Response Schema**: `BookProjectResponse`

### 1.2 GET `/api/books`
* **Purpose**: List book projects to populate the dashboard listing.
* **Query Parameters**: `PaginationParams` & `SortParams`
* **Response Schema**: `PaginatedResponse[BookProjectListItem]`

### 1.3 GET `/api/books/{book_id}`
* **Purpose**: Retrieve detailed metadata and current status for a single book project.
* **Response Schema**: `BookProjectResponse`

### 1.4 PATCH `/api/books/{book_id}`
* **Purpose**: Perform a partial update of a book project's metadata or status.
* **Request Schema**: `BookProjectUpdate`
* **Response Schema**: `BookProjectResponse`

---

## 2. Book Run Endpoints

### 2.1 POST `/api/books/{book_id}/runs`
* **Purpose**: Initialize or start a generation run for a book project.
* **Request Schema**: `BookRunCreate` or `BookRunStartRequest`
* **Response Schema**: `BookRunResponse`

### 2.2 GET `/api/runs/{run_id}`
* **Purpose**: Retrieve details of a specific execution run.
* **Response Schema**: `BookRunResponse`

### 2.3 GET `/api/runs/{run_id}/status`
* **Purpose**: Get execution monitoring metrics (real-time progress updates for the UI dashboard).
* **Response Schema**: `BookRunStatusResponse`

---

## 3. Chapter Endpoints

### 3.1 GET `/api/books/{book_id}/chapters`
* **Purpose**: List planned and generated chapters associated with a book.
* **Response Schema**: `list[ChapterListItem]`

### 3.2 GET `/api/books/{book_id}/chapters/{chapter_id}`
* **Purpose**: Retrieve complete details (including draft, humanized, and final text) of a chapter.
* **Response Schema**: `ChapterResponse`

### 3.3 PATCH `/api/books/{book_id}/chapters/{chapter_id}`
* **Purpose**: Update chapter texts, metadata, or status during humanization, editing, or fact-checking phases.
* **Request Schema**: `ChapterUpdate`
* **Response Schema**: `ChapterResponse`

### 3.4 POST `/api/books/{book_id}/chapters/insert`
* **Purpose**: Insert a new chapter after a specific chapter number.
* **Request Schema**: `ChapterInsertRequest`
* **Response Schema**: `ChapterResponse`
* **Note**: In future modules, this endpoint will trigger Test D's insertion repair workflow (correcting chapter offsets, updating the Table of Contents, aligning callback references, and appending terms to the glossary).

---

## 4. Book Section (Front/Back Matter) Endpoints

### 4.1 GET `/api/books/{book_id}/sections`
* **Purpose**: List front matter and back matter sections associated with the book.
* **Response Schema**: `list[BookSectionListItem]`

### 4.2 PATCH `/api/books/{book_id}/sections/{section_id}`
* **Purpose**: Update a specific front or back matter section (e.g. updating the assembled Table of Contents, glossary terms, or preface).
* **Request Schema**: `BookSectionUpdate`
* **Response Schema**: `BookSectionResponse`
