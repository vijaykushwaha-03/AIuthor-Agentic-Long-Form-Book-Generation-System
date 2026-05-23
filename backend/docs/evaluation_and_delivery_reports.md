# AIuthor Evaluation & Delivery Reports Documentation

This document describes the services, schemas, and endpoints added in Module 11.0 to generate final, assessment-ready delivery artifacts, prompt dossiers, qualitative evaluations, and database trace bundles.

---

## 1. Evaluation Report Checks

The `EvaluationReportService` performs programmatic, deterministic checks on four key categories:

### A. Chapter Checks (`_check_chapters`)
1. **chapter_count**: Verifies that at least one chapter structure exists in the book outline.
2. **chapter_numbering**: Confirms that chapters are sequentially numbered starting at 1.
3. **chapter_content_presence**: Validates if text content exists. Returns a `warning` status if text is found in intermediate steps but not finalized in the `final_text` column.
4. **chapter_statuses**: Ensures no chapters are marked with a `"failed"` status.
5. **chapter_word_count**: Highlights chapters containing exceptionally low word counts (< 200 words).
6. **chapter_repair_metadata**: Verifies if insert-repair metadata exists in chapter contracts or section metadata to prove self-healing validation.

### B. Export Checks (`_check_exports`)
1. **docx_export_record**: Validates if at least one ready DOCX export file is present in the database.
2. **export_file_integrity**: Probes disk storage to verify exported files exist physically.
3. **pdf_export_record**: Checks for the presence of a PDF export. Returns a `warning` if a PDF generation failed or is missing but a valid DOCX exists.

### C. Trace Checks (`_check_traces`)
1. **agent_traces_presence**: Asserts that execution traces exist in the database (returning a `warning` if missing).
2. **agent_coverage**: Evaluates the unique executed agents in the traces. Warns if any of the 8 agents are missing.
3. **prompt_logs_presence**: Audits prompt logs.
4. **token_ledger_presence**: Confirms billing token cost logs are recorded.

### D. Memory Checks (`_check_memory`)
1. **continuity_memory**: Sums total records across facts, concepts, characters, callbacks, tone fingerprints, and decisions tables. Warns if memory tables are completely empty.

---

## 2. Prompt Dossier Format

The Prompt Dossier is a compiled Markdown document displaying:
- **Inventory Table**: An index of all active agent names, versions, and role excerpts.
- **Detailed Agent Prompts**: For each agent (Planner, Researcher, Writer, Humanizer, Editor, Fact Checker, Memory Keeper, Assembler), it extracts the raw prompt template and optional rendered examples.
- **Humanizer Rules**: Mandates details regarding style, citations preservation, and tone fingerprinting.
- **Safety Rules**: Safety details (e.g. sanitization of templates to prevent secret leakages).
- **Versioning Notes**: Highlights prompt version logs in the registry.

---

## 3. Delivery Bundle Manifest

When `generate_delivery_bundle` is executed with `write_files=true`, it saves artifacts to `storage/delivery/{book_id}/{run_id_or_manual}/` and writes a `manifest.json`.

The manifest is structured as follows:
```json
{
  "book_id": "UUID-string",
  "run_id": "UUID-string-or-manual",
  "generated_at": "ISO-8601-timestamp",
  "status": "success",
  "artifacts": [
    {
      "artifact_type": "evaluation_report",
      "status": "ready",
      "file_name": "evaluation_report.md",
      "file_path": "storage/delivery/{book_id}/manual/evaluation_report.md",
      "file_size_bytes": 1024
    },
    ...
  ]
}
```

---

## 4. Manual Generation Flow

Developers can trigger these reports manually using standard REST requests:

### Step 1: Run local Uvicorn dev server
```bash
uvicorn app.main:app --reload
```

### Step 2: POST Evaluation Report
```http
POST http://127.0.0.1:8000/api/books/{book_id}/reports/evaluation
Content-Type: application/json

{
  "include_chapter_checks": true,
  "include_export_checks": true,
  "include_trace_checks": true,
  "include_memory_checks": true,
  "persist_eval_results": true,
  "metadata": {
    "manual_test": true,
    "module": "11.0"
  }
}
```

### Step 3: POST Prompt Dossier
```http
POST http://127.0.0.1:8000/api/reports/prompt-dossier
Content-Type: application/json

{
  "include_templates": true,
  "include_versions": true,
  "include_agent_roles": true,
  "include_render_examples": true
}
```

### Step 4: POST Delivery Bundle
```http
POST http://127.0.0.1:8000/api/books/{book_id}/delivery-bundle
Content-Type: application/json

{
  "include_eval_report": true,
  "include_prompt_dossier": true,
  "include_architecture_summary": true,
  "include_memory_report": true,
  "include_trace_summary": true,
  "include_export_summary": true,
  "write_files": true
}
```

### Step 5: GET Latest Bundle
```http
GET http://127.0.0.1:8000/api/books/{book_id}/delivery-bundle/latest
```

---

## 5. Security & Safety Compliance

- **No Live LLM Hits**: Evaluation metrics, template dossiers, and delivery packaging run 100% locally and deterministically.
- **No Background/Celery Workers**: Execution runs synchronously inside standard FastAPI endpoints.
- **Zero UI Dependencies**: Output files are saved directly to disk and returned as structured JSON payloads.
