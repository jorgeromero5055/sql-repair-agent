import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_url = os.environ["AGENT_DATABASE_URL"].replace(
    "postgresql://", "postgresql+psycopg://", 1
)

agent_engine = create_engine(_url, pool_pre_ping=True)

MAX_ROWS = 50

def run_sql(sql: str) -> dict:
    """Run a query on the read-only sandbox. Never raises."""
    try:
        with agent_engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result.fetchmany(MAX_ROWS)]
            return {
                "ok": True,
                "row_count": len(rows),
                "rows": rows,
                "truncated": len(rows) == MAX_ROWS,
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}