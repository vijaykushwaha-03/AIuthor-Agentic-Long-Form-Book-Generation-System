"""
Test A — End-to-end: Modern RAG Systems for AI Engineers
Runs against the live server at http://127.0.0.1:8000
"""
import json, sys
import httpx

BASE = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, timeout=300)

def post(path, body):
    r = client.post(path, json=body)
    if r.status_code >= 400:
        print(f"ERROR {r.status_code} on POST {path}: {r.text[:300]}")
        sys.exit(1)
    return r.json()

def get(path):
    r = client.get(path)
    if r.status_code >= 400:
        print(f"ERROR {r.status_code} on GET {path}: {r.text[:300]}")
        sys.exit(1)
    return r.json()

print("=== TEST A: Modern RAG Systems for AI Engineers ===\n")

# Step 1: Create book
book = post("/api/books", {
    "topic": "Modern RAG Systems for AI Engineers",
    "reader_profile": "AI Engineers, Software Architects, and Data Practitioners",
    "genre": "Technical Nonfiction",
    "tone": "conversational",
    "target_chapters": 3,
    "project_metadata": {"author": "Vijay Patel", "assessment_scenario": "Test A"}
})
book_id = book["id"]
print(f"[1] Book created: {book_id}")

# Step 2: Create 3 planned chapters
chapters_data = [
    {"chapter_number": 1, "title": "Introduction to Retrieval-Augmented Generation",
     "summary": "Fundamentals of RAG pipelines, retrieval systems, and generation steps."},
    {"chapter_number": 2, "title": "Lexical and Semantic Hybrid Retrieval",
     "summary": "Combining vector search with keyword search using BM25 and RRF."},
    {"chapter_number": 3, "title": "Production RAG Evaluation and Observability",
     "summary": "Measuring retrieval quality, token cost auditing, and step tracing."},
]
chapter_ids = []
for cd in chapters_data:
    ch = post(f"/api/books/{book_id}/chapters", {
        "book_id": book_id,
        "chapter_number": cd["chapter_number"],
        "title": cd["title"],
        "summary": cd["summary"],
        "tone": "conversational",
        "status": "planned",
    })
    chapter_ids.append(ch["id"])
    print(f"[2] Chapter {cd['chapter_number']} created: {ch['id']}")

# Step 3: Generate Chapter 1 with real Gemini
print("\n[3] Generating Chapter 1 with real Gemini (full_agent_pipeline)...")
gen = post(f"/api/books/{book_id}/chapters/generate/dev-run-real", {
    "chapter_numbers": [1],
    "workflow_name": "full_agent_pipeline",
    "execution_mode": "real_dev",
    "traced": True,
    "persist_traces": True,
    "build_context_pack": False,
    "persist_chapter_content": True,
    "overwrite_existing": True,
})
run_id = gen.get("run_id")
print(f"    run_id: {run_id}")
print(f"    status: {gen.get('status')}")
if gen.get('status') == 'failed':
    print(f"    error: {gen.get('error_message')}")
    print(f"    full response: {json.dumps(gen, indent=2)}")
items = gen.get("chapters", [])
if items:
    preview = (items[0].get("final_text") or items[0].get("content") or "")[:300]
    print(f"    content preview: {preview}...")

# Step 4: Export DOCX
print("\n[4] Exporting DOCX...")
exp = post(f"/api/books/{book_id}/exports/generate", {
    "book_id": book_id,
    "export_types": ["docx"],
    "include_front_matter": True,
    "include_back_matter": True,
    "include_toc": True,
    "include_glossary": True,
    "include_bibliography": True,
})
print(f"    export status: {exp.get('status')}")
for f in exp.get("files", []):
    print(f"    file: {f.get('file_name')} — {f.get('file_path')}")

# Step 5: Evaluation report
print("\n[5] Generating evaluation report...")
rpt = post(f"/api/books/{book_id}/reports/evaluation", {
    "book_id": book_id,
    "include_chapter_checks": True,
    "include_export_checks": True,
    "include_trace_checks": True,
    "include_memory_checks": True,
    "persist_eval_results": True,
})
print(f"    overall status: {rpt.get('status')}")
print(f"    pass={rpt.get('pass_count')} warn={rpt.get('warning_count')} fail={rpt.get('fail_count')}")
# Print quality scores
for c in rpt.get("checks", []):
    if c["check_name"] in ("ai_tells_score", "tone_consistency_score", "fact_grounding_score"):
        print(f"    {c['check_name']}: {c['status']} score={c.get('score')} — {c['message']}")

# Step 6: Delivery bundle
print("\n[6] Packaging delivery bundle...")
bundle = post(f"/api/books/{book_id}/delivery-bundle", {
    "book_id": book_id,
    "include_eval_report": True,
    "include_prompt_dossier": True,
    "include_architecture_summary": True,
    "include_trace_summary": True,
    "include_export_summary": True,
    "write_files": True,
})
print(f"    bundle status: {bundle.get('status')}")
manifest = bundle.get("manifest", {})
print(f"    artifacts: {list(manifest.keys())}")

print("\n=== TEST A COMPLETE ===")
print(f"Book ID : {book_id}")
print(f"Run ID  : {run_id}")
