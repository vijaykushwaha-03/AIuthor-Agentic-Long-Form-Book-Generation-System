from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models.observability import AgentTrace

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

book_id = "8fbfb980-91ad-4154-9130-f386a4a06ce0"
traces = db.query(AgentTrace).filter(AgentTrace.book_id == book_id).order_by(AgentTrace.created_at.asc()).all()
print(f"Total traces: {len(traces)}")
for idx, t in enumerate(traces):
    print(f"\nTrace #{idx+1}: ID={t.id}")
    print(f"  Agent: {t.agent_name}")
    print(f"  Status: {t.status}")
    print(f"  Output summary (first 300 chars):")
    out_sum = t.output_summary or ""
    print(repr(out_sum[:300]))
