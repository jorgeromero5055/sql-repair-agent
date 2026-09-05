from app.db.models import Repair, Trace
from app.sandbox import run_sql


def preview_rows(repair: Repair) -> list[dict] | None:
    """The rows the fixed query returns right now, through the read-only login.

    Nothing back if there's no fixed query, or if it doesn't run.
    """
    if not repair.fixed_query:
        return None

    result = run_sql(repair.fixed_query)

    if not result["ok"]:
        return None

    return result["rows"]


def group_attempts(trace: Trace | None) -> list[dict]:
    """Regroup the flat statement list into one entry per attempt."""
    if trace is None or not trace.statements:
        return []

    attempts: dict[int, dict] = {}

    for statement in trace.statements:
        number = statement["attempt"]

        # First statement of an attempt: open an entry for it.
        if number not in attempts:
            attempts[number] = {
                "attempt": number,
                "passed": statement["attempt_passed"],
                "reason": statement["attempt_reason"],
                "statements": [],
            }

        attempts[number]["statements"].append(
            {"sql": statement["sql"], "ok": statement["ok"]}
        )

    # Attempt 1 first, however the rows happened to be ordered.
    return [attempts[number] for number in sorted(attempts)]
