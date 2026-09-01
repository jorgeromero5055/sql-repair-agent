from sqlalchemy import create_engine, text

from app.config import AGENT_DATABASE_URL
from app.db.session import engine as app_engine

_url = AGENT_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
agent_engine = create_engine(_url, pool_pre_ping=True)

MAX_ROWS = 50


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _run(engine, sql: str) -> dict:
    # Private: it takes the login as an argument, so nothing outside this file may call it.
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [
                {k: _jsonable(v) for k, v in row._mapping.items()}
                for row in result.fetchmany(MAX_ROWS)
            ]
            return {
                "ok": True,
                "row_count": len(rows),
                "rows": rows,
                "truncated": len(rows) == MAX_ROWS,
            }
    except Exception as e:
        # A broken query is an answer, not a crash — the agent reads this and retries.
        return {"ok": False, "error": str(e)}


def run_sql(sql: str) -> dict:
    """Read-only login. The agent calls this one."""
    return _run(agent_engine, sql)


def run_sql_as_app(sql: str) -> dict:
    """The app's login. Only approval.py calls this one."""
    return _run(app_engine, sql)