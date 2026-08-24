import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_url = os.environ["AGENT_DATABASE_URL"].replace(
    "postgresql://", "postgresql+psycopg://", 1
)

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
    
from google.genai import types

RUN_SQL_DECLARATION = types.FunctionDeclaration(
    name="run_sql",
    description=(
        "Run a read-only SQL query against the sandbox schema and return the rows. "
        "Returns an error message instead of rows if the query is invalid. "
        "Use this to inspect data and to check whether a query works."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "sql": types.Schema(
                type=types.Type.STRING,
                description="A single SELECT statement. Tables live in the sandbox schema.",
            )
        },
        required=["sql"],
    ),
)