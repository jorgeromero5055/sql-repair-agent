from sqlalchemy import create_engine, text

from app.config import AGENT_DATABASE_URL

_url = AGENT_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
agent_engine = create_engine(_url, pool_pre_ping=True)

MAX_ROWS = 50


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def run_sql(sql: str) -> dict:
    """Run a query on the read-only sandbox. Never raises."""
    try:
        with agent_engine.connect() as conn:
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
        return {"ok": False, "error": str(e)}