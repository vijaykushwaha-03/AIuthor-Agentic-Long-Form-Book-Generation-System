# Manual Runner Flow Guide for Real AI Assessment Scenarios

This guide details how to invoke and execute real AI-powered assessment scenarios on the AIuthor backend.

## 1. Required Environment Setup

To run real Gemini executions, you must configure the following environment variables in your `.env` file or terminal session:

```env
ENABLE_REAL_WORKFLOW_TEST_API=true
ENABLE_REAL_MEMORY_TEST_API=true
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> [!WARNING]
> Keep your `GEMINI_API_KEY` secure. Do not commit it to version control or expose it in any public configurations.

## 2. Starting the Backend Server

Launch the FastAPI web server from the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

The interactive API documentation (Swagger) will be available at:
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. Assessment Scenarios Executions

Here are the step-by-step API requests for each assessment scenario. You can execute these via the Swagger UI or using `curl`.

---

### Scenario A: Technical Nonfiction Sample
*Topic:* `"Modern RAG Systems for AI Engineers"`
*Tone:* `"conversational"` or `"academic"`
*Expected:* 3 planned chapters, Chapter 1 generated with live Gemini, memory extraction, export DOCX, evaluation scorecard report, and delivery bundle manifest.

#### Step A.1: Create Book Project
Create a book project brief.
* **Endpoint:** `POST /api/books`
* **Payload:**
```json
{
  "topic": "Modern RAG Systems for AI Engineers",
  "reader_profile": "AI Engineers, Software Architects, and Data Practitioners",
  "genre": "Technical Nonfiction",
  "tone": "conversational",
  "target_chapters": 3,
  "project_metadata": {
    "author": "Vijay Patel",
    "assessment_scenario": "Scenario A"
  }
}
```
* **Expected Output:**
  * `id` (referred to below as `<book_id>`)

#### Step A.2: Create Planned Chapters
Create the structure. Submit this payload for Chapter 1, 2, and 3:
* **Endpoint:** `POST /api/books/{book_id}/chapters`
* **Payload (Chapter 1):**
```json
{
  "book_id": "<book_id>",
  "chapter_number": 1,
  "title": "Introduction to Retrieval-Augmented Generation",
  "summary": "Introduction to RAG pipelines, retrieval systems, and generation steps.",
  "chapter_contract": {
    "chapter_number": 1,
    "title": "Introduction to Retrieval-Augmented Generation",
    "purpose": "Lay down fundamentals of RAG systems.",
    "key_concepts": ["Retrieval", "Generation", "Vector Embeddings"],
    "required_facts": ["RAG combines lexical or semantic vector search with LLMs."],
    "callback_opportunities": []
  },
  "tone": "conversational",
  "status": "planned"
}
```
* **Payload (Chapter 2):**
```json
{
  "book_id": "<book_id>",
  "chapter_number": 2,
  "title": "Lexical and Semantic Hybrid Retrieval",
  "summary": "Deep dive into combining vector search with keyword search.",
  "chapter_contract": {
    "chapter_number": 2,
    "title": "Lexical and Semantic Hybrid Retrieval",
    "purpose": "Explain how hybrid retrieval works.",
    "key_concepts": ["Hybrid Search", "Reciprocal Rank Fusion", "BM25"],
    "required_facts": ["BM25 remains a solid exact matching benchmark."],
    "callback_opportunities": ["Introduction to Retrieval-Augmented Generation"]
  },
  "tone": "conversational",
  "status": "planned"
}
```
* **Payload (Chapter 3):**
```json
{
  "book_id": "<book_id>",
  "chapter_number": 3,
  "title": "Production RAG Evaluation and Observability",
  "summary": "Methods to measure retrieval quality, token cost auditing, and step tracing.",
  "chapter_contract": {
    "chapter_number": 3,
    "title": "Production RAG Evaluation and Observability",
    "purpose": "Detail QA and metrics reporting.",
    "key_concepts": ["Observability", "Traces", "Evaluation Scorecards"],
    "required_facts": ["Observability tracing is key to troubleshooting agent steps."],
    "callback_opportunities": ["Introduction to Retrieval-Augmented Generation", "Lexical and Semantic Hybrid Retrieval"]
  },
  "tone": "conversational",
  "status": "planned"
}
```

#### Step A.3: Generate Chapter 1 (Real Gemini)
Generate Chapter 1 content using the dev-real generation endpoint:
* **Endpoint:** `POST /api/books/{book_id}/chapters/generate/dev-run-real`
* **Payload:**
```json
{
  "chapter_numbers": [1],
  "workflow_name": "full_agent_pipeline",
  "execution_mode": "real_dev",
  "traced": true,
  "persist_traces": true,
  "build_context_pack": false,
  "persist_chapter_content": true,
  "overwrite_existing": true
}
```
* **Expected Output:**
  * `run_id` (referred to below as `<run_id>`)
  * `chapters`: List of chapter generation summaries with chapter text.

#### Step A.4: Extract Memory (Real Gemini)
Extract facts, concepts, and tone fingerprints from Chapter 1 using MemoryKeeper:
* **Endpoint:** `POST /api/books/{book_id}/memory/extract/dev-run-real`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "run_id": "<run_id>",
  "source_type": "chapter",
  "chapter_id": "<chapter_1_uuid>",
  "execution_mode": "real_dev",
  "persist_memory": true,
  "overwrite_existing": true
}
```
* **Expected Output:**
  * `written_count` (number of records written to DB)
  * `candidates`: List of candidates parsed.

#### Step A.5: Export DOCX/PDF
Assemble the manuscript files on disk:
* **Endpoint:** `POST /api/books/{book_id}/exports/generate`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "run_id": "<run_id>",
  "export_types": ["docx", "pdf"],
  "include_front_matter": true,
  "include_back_matter": true,
  "include_toc": true,
  "include_glossary": true,
  "include_bibliography": true
}
```
* **Expected Output:**
  * `status`: `"ready"`
  * `files`: List of generated file names and paths in `storage/exports`.

#### Step A.6: Generate Evaluation Report
Create the qualitative scorecard validation report:
* **Endpoint:** `POST /api/books/{book_id}/reports/evaluation`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "run_id": "<run_id>",
  "include_chapter_checks": true,
  "include_export_checks": true,
  "include_trace_checks": true,
  "include_memory_checks": true,
  "persist_eval_results": true
}
```
* **Expected Output:**
  * `status`: `"pass"` or `"warning"`
  * `markdown_report`: Fully rendered evaluation scorecard.

#### Step A.7: Generate Delivery Bundle
Assemble delivery bundle (dossier, trace bundle, metadata summaries):
* **Endpoint:** `POST /api/books/{book_id}/delivery-bundle`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "run_id": "<run_id>",
  "include_eval_report": true,
  "include_prompt_dossier": true,
  "include_architecture_summary": true,
  "include_memory_report": true,
  "include_trace_summary": true,
  "include_export_summary": true,
  "write_files": true
}
```
* **Expected Output:**
  * `status`: `"ready"`
  * `manifest`: JSON manifest with listing of all artifacts saved in `storage/delivery/<book_id>/`.

---

### Scenario B: Fiction / Creative Sample
*Topic:* `"The Clockmaker of Silent City"`
*Tone:* `"storyteller"`
*Expected:* Demonstrate tone control, character memory extraction, continuity pack compilation.

#### Step B.1: Create Creative Book Project
* **Endpoint:** `POST /api/books`
* **Payload:**
```json
{
  "topic": "The Clockmaker of Silent City",
  "reader_profile": "General Fiction readers looking for atmospheric storytelling",
  "genre": "Creative Fiction / Speculative",
  "tone": "storyteller",
  "target_chapters": 3,
  "project_metadata": {
    "author": "Vijay Patel",
    "assessment_scenario": "Scenario B"
  }
}
```

#### Step B.2: Create Planned Chapter 1
* **Endpoint:** `POST /api/books/{book_id}/chapters`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "chapter_number": 1,
  "title": "The First Gears Turn",
  "summary": "Introduce Master Benjamin, the central grandfather clock tower, and the mist that falls over the Silent City at sundown.",
  "chapter_contract": {
    "chapter_number": 1,
    "title": "The First Gears Turn",
    "purpose": "Introduce the clockmaker and the atmospheric setting.",
    "key_concepts": ["Silent City", "Benjamin", "Aether Clock"],
    "required_facts": ["Benjamin has worked in the main clock tower for forty years.", "No noise is permitted after sunset."],
    "callback_opportunities": []
  },
  "tone": "storyteller",
  "status": "planned"
}
```

#### Step B.3: Generate Chapter 1 (Real Gemini)
Generate and persist creative chapter content enforcing narrative tone:
* **Endpoint:** `POST /api/books/{book_id}/chapters/generate/dev-run-real`
* **Payload:**
```json
{
  "chapter_numbers": [1],
  "workflow_name": "full_agent_pipeline",
  "execution_mode": "real_dev",
  "traced": true,
  "persist_chapter_content": true
}
```

#### Step B.4: Extract Character Memory (Real Gemini)
Extract Master Benjamin's lore and setting concepts to the database memory keepers:
* **Endpoint:** `POST /api/books/{book_id}/memory/extract/dev-run-real`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "run_id": "<run_id>",
  "source_type": "chapter",
  "chapter_id": "<chapter_1_uuid>",
  "execution_mode": "real_dev",
  "include_characters": true,
  "include_concepts": true,
  "persist_memory": true
}
```

#### Step B.5: Generate Continuity Pack
Build a markdown continuity summary compiled from character and fact registries to pass to next nodes:
* **Endpoint:** `POST /api/books/{book_id}/memory/continuity-pack`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "include_facts": true,
  "include_concepts": true,
  "include_characters": true,
  "include_callbacks": true,
  "max_items_per_type": 20,
  "max_chars": 12000
}
```
* **Expected Output:**
  * `continuity_text`: Rendered markdown continuity pack.

---

### Scenario C: Dense Knowledge Sample
*Topic:* `"AI Agents for Enterprise Automation"`
*Tone:* `"academic"`
*Expected:* RAG context packaging, cited generation, output DOCX.

#### Step C.1: Create Book Project
* **Endpoint:** `POST /api/books`
* **Payload:**
```json
{
  "topic": "AI Agents for Enterprise Automation",
  "reader_profile": "CTOs, Enterprise Architects, and Technical Managers",
  "genre": "Technical Reference",
  "tone": "academic",
  "target_chapters": 3,
  "project_metadata": {
    "author": "Vijay Patel",
    "assessment_scenario": "Scenario C"
  }
}
```

#### Step C.2: Create Planned Chapter 1
* **Endpoint:** `POST /api/books/{book_id}/chapters`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "chapter_number": 1,
  "title": "Orchestrating Autonomous Workflows",
  "summary": "State machines, LangGraph architectures, and context boundary routing in enterprises.",
  "chapter_contract": {
    "chapter_number": 1,
    "title": "Orchestrating Autonomous Workflows",
    "purpose": "Define graph orchestration patterns.",
    "key_concepts": ["State Graph", "Node Boundaries", "Persistence Layer"],
    "required_facts": ["State graphs provide robust error tracking and recovery."],
    "callback_opportunities": []
  },
  "tone": "academic",
  "status": "planned"
}
```

#### Step C.3: Populate RAG Source Documents
Upload enterprise reference documentation if it exists, or create a mock reference source document to simulate RAG retrieval:
* **Endpoint:** `POST /api/books/{book_id}/sources`
* **Payload:**
```json
{
  "title": "Enterprise Agent Architecture Whitepaper",
  "source_type": "pdf",
  "raw_content": "LangGraph is designed for cyclic agent networks. Enterprise automation requires state persistence and human-in-the-loop gates to verify critical steps before committing transactions.",
  "status": "processed"
}
```
* **Expected Output:**
  * `id` (referred to as `<document_id>`)

#### Step C.4: Chunk Reference Document
Chunk and prepare vectors:
* **Endpoint:** `POST /api/sources/{document_id}/chunk`
* **Payload:**
```json
{
  "chunk_size": 200,
  "chunk_overlap": 50
}
```

#### Step C.5: Generate Chapter 1 with Citations (Real Gemini)
Generate the chapter, automatically compiling vector matching context packs:
* **Endpoint:** `POST /api/books/{book_id}/chapters/generate/dev-run-real`
* **Payload:**
```json
{
  "chapter_numbers": [1],
  "workflow_name": "full_agent_pipeline",
  "execution_mode": "real_dev",
  "build_context_pack": true,
  "max_context_chunks": 5,
  "context_query_template": "LangGraph state persistence and enterprise workflows",
  "persist_chapter_content": true
}
```

#### Step C.6: Export DOCX
Assemble referenced source bibliography alongside chapter outputs:
* **Endpoint:** `POST /api/books/{book_id}/exports/generate`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "export_types": ["docx"],
  "include_bibliography": true
}
```

---

### Scenario D: Insert Chapter Self-Healing Sample
*Expected:* Insert a new chapter at index/position 2. Later chapters shift index numbering, repair items are logged for table of contents, continuity callback references, glossary, and back matter. Trace bundle generated.

#### Step D.1: Prepare Pre-existing Book
Use any existing generated book project (from Scenario A, B, or C) containing 3 chapters.

#### Step D.2: Insert Chapter at Position 2 (Real Gemini)
Insert a chapter at position 2 and run self-healing repairs:
* **Endpoint:** `POST /api/books/{book_id}/chapters/insert-repair/dev-run-real`
* **Payload:**
```json
{
  "book_id": "<book_id>",
  "insert_at_chapter_number": 2,
  "title": "Advanced Retrieval Strategy Alternatives",
  "summary": "Exploring query expansion, hypothetical document embeddings (HyDE), and multi-vector tables.",
  "generate_content": true,
  "workflow_name": "full_agent_pipeline",
  "execution_mode": "real_dev",
  "repair_toc": true,
  "repair_callbacks": true,
  "repair_glossary": true,
  "repair_back_matter": true,
  "overwrite_existing_repair": true
}
```
* **Expected Output:**
  * `inserted_chapter_id`: UUID of the new chapter.
  * `affected_chapter_ids`: Chapter UUIDs shifted forward.
  * `repair_items`: List of generated repair actions (e.g. TOC rebuilt, callback indices updated, glossary updated).
  * `trace_bundle`: Detailed LangGraph steps execution logs.
