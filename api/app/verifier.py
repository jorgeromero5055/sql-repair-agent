from app.sandbox import run_sql


def check(sql: str) -> dict:
    """Does this query run? Used in production, inside the repair loop."""
    result = run_sql(sql)

    if not result["ok"]:
        return {"passed": False, "reason": f"The query failed: {result['error']}"}

    return {"passed": True, "reason": f"Query runs, returned {result['row_count']} rows."}
