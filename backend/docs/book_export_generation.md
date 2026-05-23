# Book Assembly & Document Export (Module 10.0)

This document provides details on how the book assembler and export services compile written chapter texts and other book components into publication-ready manuscripts and generate physical `.docx` and `.pdf` files.

---

## 1. Book Assembly Pipeline
Book assembly compiles various parts of the book project without altering any database content or calling any LLM.
- **Chapter Text Selection**: Dynamically selects the best available version of chapter content per chapter (by default: `final_text` -> `edited_text` -> `humanized_text` -> `draft_text` -> `summary`).
- **Front Matter Sections**: Loads existing `BookSection` records marked as front matter. If none exist in the database, it constructs virtual front matter placeholders for Title Page, Copyright, and Table of Contents (TOC).
- **Back Matter Sections**: Loads existing `BookSection` records marked as back matter. If none exist, it creates virtual back matter entries: Conclusion, Glossary (populated from `ConceptBible`), and Bibliography (populated from `SourceDocument`).
- **Word Counts**: Computes total word counts per chapter and for the entire book.

---

## 2. DOCX Export Generation
The system generates a structured `.docx` file using `python-docx`:
- **Title Page layout**: Custom font sizing, centered text, and spacers for Title, Subtitle, and Author details.
- **TOC**: Renders the table of contents lists pointing to the generated chapters.
- **Manuscript Formatting**: Automatically structures sections (preface, foreword, chapters, glossary, bibliography) separated by clean page breaks.

---

## 3. PDF Export Generation via LibreOffice
PDF generation is built using headless LibreOffice:
- **Conversion Command**: Calls the system shell command `soffice --headless --convert-to pdf --outdir <dir> <docx_path>`.
- **System Detection**: The backend searches for the `soffice`/`libreoffice` command in the environment `PATH`, and also searches standard installation directories on Windows (e.g. `C:\Program Files\LibreOffice\program\soffice.exe`) as a backup.
- **Fallback Behavior**: If LibreOffice is not found, PDF generation fails gracefully, logging the failure status to the database, but keeping the successful DOCX file export.

---

## 4. Export Configurations and Storage
- **`EXPORT_OUTPUT_DIR`** (defaults to `storage/exports` relative to the backend root): Output files are saved in the format: `storage/exports/{book_id}/{run_id_or_manual}/{safe_title}_{timestamp}.{docx/pdf}`.
- **`ENABLE_PDF_EXPORT`** (defaults to `true`): Allows disabling PDF exports globally if needed.

---

## 5. ExportFile DB Tracking
Each exported file gets a row in the `export_files` table containing:
- `book_id`, `run_id` (if run context available)
- `export_type` ("docx" or "pdf")
- `file_path`, `file_name`, `mime_type`
- `status` ("ready" on success, "failed" on error)
- `export_metadata` (including file size in bytes, timestamp, or any error message if it failed)

---

## 6. API Endpoints Usage

### Generate DOCX Only
Perform a POST request:
`POST /api/books/{book_id}/exports/generate`

Body:
```json
{
  "export_types": ["docx"],
  "include_front_matter": true,
  "include_back_matter": true,
  "include_toc": true,
  "include_glossary": true,
  "include_bibliography": true,
  "overwrite_existing": true
}
```

### Generate DOCX + PDF
Perform a POST request:
`POST /api/books/{book_id}/exports/generate`

Body:
```json
{
  "export_types": ["docx", "pdf"],
  "include_front_matter": true,
  "include_back_matter": true,
  "include_toc": true,
  "include_glossary": true,
  "include_bibliography": true,
  "overwrite_existing": true
}
```

---

## 7. Testing Architecture
- **Offline Isolation**: All tests run fully offline.
- **LibreOffice Mocking**: The PDF conversion method (`convert_docx_to_pdf`) is monkeypatched in the test suite to bypass actual LibreOffice execution. Pytest does not require LibreOffice to be installed.
- **No LLM calls**: Assembly and exports do not invoke any LLM or require Gemini/OpenAI API keys in tests.
- **Safety**: No background workers or Celery task queues are utilized. Everything is executed synchronously at the endpoint controller layer.
