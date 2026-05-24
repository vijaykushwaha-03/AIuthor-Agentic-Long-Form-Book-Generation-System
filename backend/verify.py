import os
os.environ["APP_ENV"] = "development"

results = {}

with open("app/workflows/state.py") as f:
    src = f.read()
results["state: retry_count field"] = "retry_count: int" in src
results["state: retry_count initialized"] = "retry_count=0" in src

with open("app/workflows/graph.py") as f:
    src = f.read()
results["graph: add_conditional_edges"] = "add_conditional_edges" in src
results["graph: _fact_check_router defined"] = "def _fact_check_router" in src
results["graph: MAX_FACT_CHECK_RETRIES=2"] = "MAX_FACT_CHECK_RETRIES = 2" in src
results["graph: writer retry target"] = '"writer": "writer"' in src
results["graph: memory_keeper target"] = '"memory_keeper": "memory_keeper"' in src

with open("app/workflows/nodes.py") as f:
    src = f.read()
results["nodes: retry_count increment"] = "retry_count += 1" in src
results["nodes: checks fact_checker_output for retry"] = 'state.get("fact_checker_output") is not None' in src

with open("app/services/evaluation_report_service.py") as f:
    src = f.read()
results["eval: _check_ai_tells method"] = "def _check_ai_tells" in src
results["eval: _check_tone_consistency method"] = "def _check_tone_consistency" in src
results["eval: _check_fact_grounding method"] = "def _check_fact_grounding" in src
results["eval: AI_TELLS phrase list"] = "_AI_TELLS" in src
results["eval: scorers wired in generate_report"] = "self._check_ai_tells(request.book_id)" in src
results["eval: Quality Scores in markdown"] = "Quality Scores" in src

print("\n=== IMPLEMENTATION VERIFICATION ===\n")
all_pass = True
for name, ok in results.items():
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {name}")

print()
print("OVERALL:", "ALL PASS" if all_pass else "SOME FAILURES")
