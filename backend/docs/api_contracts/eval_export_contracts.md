# Evaluation & Export API Contracts

This document describes the HTTP endpoints for backend evaluation and export file services, including automated evaluation logging, report summaries, output file management, export requests, and consolidated export bundles in the AIuthor backend.

> [!NOTE]
> **Module 4.2D Implemented**: All endpoints below are live.
> **No Real Evaluation Runner** is implemented in this module; reports only summarize stored evaluation result records.
> **No Real DOCX/PDF Generation** is implemented; export requests write virtual placeholder records mapped to `pending://` URIs.
> **No physical files are created** on disk yet.

---

## 1. Evaluation Result Endpoints ✅ Implemented (Module 4.2D)

Evaluation results store automated evaluation quality metrics (e.g. readability, structure, lexical compliance) mapped to a specific `BookProject` and optionally a `BookRun`.

### 1.1 POST `/api/books/{book_id}/evals`
* **Purpose**: Create a new evaluation result for a book project.
* **Request Schema**: `EvalResultCreate`
* **Response Schema**: `EvalResultResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `book_id` is the source of truth. Raises `404` if the book project does not exist.

### 1.2 GET `/api/books/{book_id}/evals`
* **Purpose**: List evaluation results for a book project (paginated, sorted newest-first by `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `eval_name: str | None` — filter by evaluation metric name
  - `status: str | None` — filter by status (`passed`, `failed`, `warning`, `skipped`)
  - `run_id: UUID | None` — optional filter by linked execution run
* **Response Schema**: `PaginatedResponse[EvalResultResponse]`

### 1.3 GET `/api/books/{book_id}/evals/{eval_id}`
* **Purpose**: Retrieve full details of a specific evaluation result scoped to a book.
* **Response Schema**: `EvalResultResponse`

### 1.4 PATCH `/api/books/{book_id}/evals/{eval_id}`
* **Purpose**: Partial update of an evaluation result (e.g. updating metric score or status).
* **Request Schema**: `EvalResultUpdate`
* **Response Schema**: `EvalResultResponse`

### 1.5 DELETE `/api/books/{book_id}/evals/{eval_id}`
* **Purpose**: Permanently delete an evaluation result.
* **Response Schema**: `MessageResponse`

### 1.6 GET `/api/books/{book_id}/eval-report`
* **Purpose**: Compile and summarize all stored evaluation results for a book into a unified evaluation report.
* **Query Parameters**:
  - `run_id: UUID | None` — optional filter by linked execution run
* **Response Schema**: `EvalReportResponse`
* **Notes**: Automatically aggregates statistics, including `total_evals`, `passed_evals`, `failed_evals`, `warning_evals`, and computes `overall_score` (average of non-null scores) and `overall_status` (`failed`, `warning`, `passed`, or `empty`).

### 1.7 POST `/api/runs/{run_id}/evals`
* **Purpose**: Create a new evaluation result for a run.
* **Request Schema**: `EvalResultCreate`
* **Response Schema**: `EvalResultResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `run_id` is the source of truth. The `book_id` is resolved from the run record if available.

---

## 2. Export File Endpoints ✅ Implemented (Module 4.2D)

Export files store metadata and paths for generated output file types (e.g., Docx, PDF, Prompt Dossier, Trace Bundle).

### 2.1 POST `/api/books/{book_id}/exports`
* **Purpose**: Create a new export file record.
* **Request Schema**: `ExportFileCreate`
* **Response Schema**: `ExportFileResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `book_id` is the source of truth.

### 2.2 GET `/api/books/{book_id}/exports`
* **Purpose**: List export files for a book project (paginated, sorted newest-first by `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `export_type: str | None` — filter by type (`docx`, `pdf`, `trace_bundle`, etc.)
  - `status: str | None` — filter by status (`created`, `ready`, `failed`)
  - `run_id: UUID | None` — optional filter by linked run
* **Response Schema**: `PaginatedResponse[ExportFileListItem]`

### 2.3 POST `/api/books/{book_id}/exports/request`
* **Purpose**: Request file generation for one or more export formats.
* **Request Schema**: `ExportRequest`
* **Response Schema**: `ExportResponse`
* **Status Code**: `200 OK`
* **Notes**: Path `book_id` is the source of truth. Creates virtual placeholder `ExportFile` records with `status = "created"`, mapped to `pending://exports/{book_id}/{export_type}`. No physical files are written to disk.

### 2.4 GET `/api/books/{book_id}/exports/bundle`
* **Purpose**: Compile a bundle overview of all exports generated for a book project.
* **Query Parameters**:
  - `run_id: UUID | None` — optional filter by linked execution run
* **Response Schema**: `ExportBundleResponse`
* **Notes**: Summarizes total files, ready files, failed files, and returns overall bundle status (`empty`, `failed`, `ready`, or `partial`).

### 2.5 GET `/api/books/{book_id}/exports/{export_id}`
* **Purpose**: Retrieve details of a specific export record.
* **Response Schema**: `ExportFileResponse`

### 2.6 PATCH `/api/books/{book_id}/exports/{export_id}`
* **Purpose**: Update export file status or metadata.
* **Request Schema**: `ExportFileUpdate`
* **Response Schema**: `ExportFileResponse`

### 2.7 DELETE `/api/books/{book_id}/exports/{export_id}`
* **Purpose**: Permanently delete an export file record from the database.
* **Response Schema**: `MessageResponse`
* **Notes**: DB record is deleted; no physical files on disk are touched.

### 2.8 GET `/api/runs/{run_id}/exports`
* **Purpose**: List export file items scoped to a run.
* **Response Schema**: `PaginatedResponse[ExportFileListItem]`
