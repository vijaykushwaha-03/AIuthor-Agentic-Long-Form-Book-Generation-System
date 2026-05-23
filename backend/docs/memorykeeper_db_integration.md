# MemoryKeeper DB Integration

This document outlines the architecture, candidate mappings, formatting rules, and safety controls for the MemoryKeeper DB Integration (Module 9.0).

## 1. Overview
The MemoryKeeper DB Integration allows AIuthor to extract stable narrative continuity records from raw text, outline documents, or workflow traces, and persist them into the project's long-term database-backed memory. This memory is then compiled into a structured markdown document (a **Continuity Pack**) that subsequent generation and editing agents consume to maintain narrative consistency.

---

## 2. Memory Candidate Types & DB Mappings
The extraction service returns structured candidates of 6 distinct memory types. These candidates map directly to existing memory models/tables:

| Memory Candidate Type | DB Model / Table | Mapping Logic | Unique Constraint / Duplicate Check |
| :--- | :--- | :--- | :--- |
| **fact** | `FactRegistry` | `claim` = candidate value, `confidence` = candidate confidence. | Checked by `claim` matching. |
| **concept** | `ConceptBible` | `concept` = candidate key, `definition` = candidate value. | UniqueConstraint on `(book_id, concept)`. |
| **character** | `CharacterBible` | `character_name` = candidate key, `role` = candidate value. | UniqueConstraint on `(book_id, character_name)`. |
| **callback** | `CallbackIndex` | `concept` = candidate key, `callback_text` = candidate value. Source/target chapters loaded from metadata. | Checked by `callback_text` matching. |
| **tone** | `ToneFingerprint` | `tone_name` = candidate key. Sentence rhythm, lexical rules, and phrase lists stored in properties. | Checked by `tone_name` matching. |
| **decision** | `DecisionLog` | `decision` = candidate key, `reason` = candidate value. | Checked by `decision` matching. |

When `overwrite_existing=False` and a duplicate is found, the record is skipped. When `overwrite_existing=True`, the record is updated in place using the service's update methods.

---

## 3. Extraction Modes
The module supports two execution modes:

### A. Mock Extraction (`mock`)
- Deterministic, runs fully offline.
- No LLM calls.
- Scans input text and generates predictable candidates (e.g. searching for keywords like "RAG", "John", "later" to generate concepts, characters, and callbacks).
- Used in all automated pytests.

### B. Real Dev Extraction (`real_dev`)
- Gated dev-only route.
- Invokes the `MemoryKeeper` agent via `AgentExecutionService.run_agent_once`.
- Gated by the `ENABLE_REAL_MEMORY_TEST_API` environment variable.
- Returns `403 Forbidden` if disabled.

---

## 4. Continuity Pack Format
The Continuity Pack compiles memory tables into a structured markdown document. It respects `max_items_per_type` and restricts the total character size to `max_chars` by truncating gracefully at item boundaries.

Example layout:
```markdown
# Continuity Pack

## Facts
- Dragons can breathe fire. (Confidence: 0.95)

## Concepts
- Mana: Magical fuel.

## Characters
- Alice (Role: Protagonist): Becomes a leader. Traits: brave, loyal

## Callbacks
- Callback (Concept: Ring): Return ring to volcano. (Ch 1 -> Ch 3)

## Tone Fingerprints
- Tone: storyteller (Rhythm: {"average_sentence_length": 14})

## Decisions
- Decision: Use SQLite in-memory (Reason: Performance)
```

---

## 5. Setup for Manual Dev Testing
To test the real Gemini memory extraction locally:

1. Configure `backend/.env`:
   ```bash
   ENABLE_REAL_MEMORY_TEST_API=true
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=<your_real_key>
   GEMINI_MODEL=gemini-2.5-flash
   ```

2. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

3. Call the real chapter extraction endpoint:
   - **Method**: `POST`
   - **URL**: `http://127.0.0.1:8000/api/books/{book_id}/memory/extract/from-chapter/{chapter_id}/dev-run-real`
   - **Body**:
     ```json
     {
       "book_id": "{book_id}",
       "source_type": "chapter",
       "persist_memory": true,
       "include_facts": true,
       "include_concepts": true,
       "include_characters": true,
       "include_callbacks": true,
       "include_tone": true,
       "include_decisions": true,
       "metadata": {
         "manual_test": true,
         "module": "9.0"
       }
     }
     ```

4. Retrieve the Continuity Pack:
   - **Method**: `POST`
   - **URL**: `http://127.0.0.1:8000/api/books/{book_id}/memory/continuity-pack`
   - **Body**:
     ```json
     {
       "book_id": "{book_id}",
       "include_facts": true,
       "include_concepts": true,
       "include_characters": true,
       "include_callbacks": true,
       "include_tone": true,
       "include_decisions": true,
       "max_items_per_type": 20,
       "max_chars": 12000
     }
     ```

---

## 6. Safety & Restrictions
- **Pytest Isolation**: Automated pytests are 100% offline and use only `mock` execution mode. They do not invoke LLMs or require API keys.
- **No Background Jobs**: Real-time extraction runs synchronously on the route call. No celery or redis tasks are introduced.
- **No UI Changes**: React templates or UI packages are not included.
