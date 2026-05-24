import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.observability import AgentTrace
from app.models import BookRun

DATABASE_URL = "postgresql+psycopg2://aiuthor:aiuthor_secret@127.0.0.1:5433/aiuthor_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

run_id = sys.argv[1]
run = db.query(BookRun).filter(BookRun.id == run_id).first()
print(f"BookRun: {run.status if run else 'Not Found'} - {run.error_message if run else ''}")

traces = db.query(AgentTrace).filter(AgentTrace.run_id == run_id).order_by(AgentTrace.created_at).all()
for t in traces:
    print(f"Agent: {t.agent_name} Status: {t.status} Error: {t.error_message}")
