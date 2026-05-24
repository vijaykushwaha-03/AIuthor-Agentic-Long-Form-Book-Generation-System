import os
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["EMBEDDING_DIMENSIONS"] = "8"
os.environ["RAG_VECTOR_DIMENSIONS"] = "8"

# ── 1. Graph compiles and conditional edge works ──────────────────────────────
print("=== TEST 1: LangGraph conditional edge ===")

from app.config import get_settings
get_settings.cache_clear()

from app.workflows.graph import build_full_agent_workflow, _fact_check_router, MAX_FACT_CHECK_RETRIES
from app.workflows.state import AIuthorWorkflowState

graph = build_full_agent_workflow()
print(f"  Graph compiled OK — nodes: {list(graph.nodes.keys())}")

# Test router: no failure → memory_keeper
state_ok: AIuthorWorkflowState = {
    "workflow_name": "full_agent_pipeline", "execution_mode": "mock",
    "run_id": None, "book_id": None, "chapter_id": None,
    "topic": "test", "genre": None, "reader_profile": None, "tone": None,
    "task": None, "context_pack": None, "memory_context": None,
    "payload": None, "metadata": {},
    "planner_output": None, "researcher_output": None, "writer_output": None,
    "humanizer_output": None, "editor_output": None,
    "fact_checker_output": {"structured_output": {"overall_confidence": 0.9, "fact_check_report": []}},
    "memory_keeper_output": None, "assembler_output": None,
    "steps": [], "status": "running", "error_message": None,
    "retry_count": 0, "persist_traces": False, "trace_steps": [], "trace_bundle": None,
}
route = _fact_check_router(state_ok)
assert route == "memory_keeper", f"Expected memory_keeper, got {route}"
print(f"  Router (confidence=0.9, retry=0) → {route}  ✓")

# Test router: low confidence → writer retry
state_fail = {**state_ok, "fact_checker_output": {"structured_output": {"overall_confidence": 0.5, "fact_check_report": []}}, "retry_count": 0}
route2 = _fact_check_router(state_fail)
assert route2 == "writer", f"Expected writer, got {route2}"
print(f"  Router (confidence=0.5, retry=0) → {route2}  ✓")

# Test router: max retries reached → memory_keeper
state_maxretry = {**state_fail, "retry_count": MAX_FACT_CHECK_RETRIES}
route3 = _fact_check_router(state_maxretry)
assert route3 == "memory_keeper", f"Expected memory_keeper after max retries, got {route3}"
print(f"  Router (confidence=0.5, retry={MAX_FACT_CHECK_RETRIES}) → {route3}  ✓")

# Test router: unsupported claim → writer retry
state_unsupported = {**state_ok, "fact_checker_output": {
    "structured_output": {"overall_confidence": 0.8, "fact_check_report": [{"status": "unsupported", "claim": "x"}]}
}, "retry_count": 0}
route4 = _fact_check_router(state_unsupported)
assert route4 == "writer", f"Expected writer for unsupported claim, got {route4}"
print(f"  Router (unsupported claim, retry=0) → {route4}  ✓")

# ── 2. Mock pipeline runs end-to-end ─────────────────────────────────────────
print("\n=== TEST 2: Full pipeline mock run ===")
from app.workflows.schemas import WorkflowInput
from app.workflows.graph import run_full_agent_workflow

inp = WorkflowInput(
    workflow_name="full_agent_pipeline",
    topic="Modern RAG Systems",
    genre="Technical Nonfiction",
    tone="conversational",
    reader_profile="AI Engineers",
)
out = run_full_agent_workflow(inp, execution_mode="mock")
print(f"  Status: {out.status}")
print(f"  Steps completed: {len(out.steps)}")
print(f"  Final content present: {bool(out.final_content)}")
assert out.status == "completed", f"Expected completed, got {out.status}"
assert len(out.steps) >= 8, f"Expected 8 steps, got {len(out.steps)}"
print("  Full pipeline mock run  ✓")

# ── 3. Eval scorers run against in-memory DB ──────────────────────────────────
print("\n=== TEST 3: Eval quality scorers ===")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.models  # register all models

from app.database import Base
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# Create a book + chapter with AI-tell-heavy text
import uuid
from app.models.book import BookProject
from app.models.chapter import Chapter

book = BookProject(
    id=uuid.uuid4(), topic="RAG Systems", reader_profile="Engineers",
    genre="Technical Nonfiction", tone="conversational", target_chapters=1, status="created"
)
db.add(book)
db.flush()

ch = Chapter(
    id=uuid.uuid4(), book_id=book.id, chapter_number=1,
    title="Intro", status="completed",
    final_text="In conclusion, it is worth noting that we should leverage AI. Furthermore, in today's world, this is a game-changer. Let's think about how you can utilize this approach. Actually, imagine the possibilities.",
)
db.add(ch)
db.commit()

from app.services.evaluation_report_service import EvaluationReportService
svc = EvaluationReportService(db)

# AI tells
ai_checks = svc._check_ai_tells(book.id)
print(f"  ai_tells_score: status={ai_checks[0].status} score={ai_checks[0].score} hits={ai_checks[0].details.get('total_hits')}")
assert ai_checks[0].check_name == "ai_tells_score"
assert ai_checks[0].details["total_hits"] > 0
print("  AI tells scorer  ✓")

# Tone consistency
tone_checks = svc._check_tone_consistency(book.id)
print(f"  tone_consistency_score: status={tone_checks[0].status} score={tone_checks[0].score}")
assert tone_checks[0].check_name == "tone_consistency_score"
print("  Tone consistency scorer  ✓")

# Fact grounding (no facts → skipped)
fg_checks = svc._check_fact_grounding(book.id)
print(f"  fact_grounding_score: status={fg_checks[0].status}")
assert fg_checks[0].check_name == "fact_grounding_score"
assert fg_checks[0].status == "skipped"  # no facts in DB
print("  Fact grounding scorer (skipped — no facts)  ✓")

# Add a grounded and ungrounded fact, re-test
from app.models.memory import FactRegistry
db.add(FactRegistry(id=uuid.uuid4(), book_id=book.id, claim="RAG uses vectors", source_chunk_id=uuid.uuid4(), status="verified"))
db.add(FactRegistry(id=uuid.uuid4(), book_id=book.id, claim="Ungrounded claim", source_chunk_id=None, status="unverified"))
db.commit()
fg2 = svc._check_fact_grounding(book.id)
print(f"  fact_grounding_score (1/2 grounded): status={fg2[0].status} score={fg2[0].score}")
assert fg2[0].score == 0.5
print("  Fact grounding scorer (0.5)  ✓")

db.close()
print("\n=== ALL TESTS PASSED ===")
