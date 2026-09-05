"""The oracle: does this query produce the same answer as the correct one?

Only the eval uses this. It compares result sets, never query text — two queries can be written
completely differently and still both be right.
"""

from decimal import Decimal

from app.sandbox import run_sql


def _normalise(rows: list[dict]) -> list[tuple]:
    """Turn rows into something order-independent and type-insensitive."""
    normalised = []
    for row in rows:
        items = []
        for key in sorted(row):
            value = row[key]
            if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
                value = float(value)
            items.append((key, value))
        normalised.append(tuple(items))
    return sorted(normalised, key=repr)


def compare(candidate_sql: str, reference_sql: str) -> dict:
    """Do these two queries produce the same result set? Used only in the eval."""
    candidate = run_sql(candidate_sql)
    if not candidate["ok"]:
        return {"passed": False, "reason": f"The query failed: {candidate['error']}"}

    reference = run_sql(reference_sql)
    if not reference["ok"]:
        return {
            "passed": False,
            "reason": f"Reference query failed, cannot compare: {reference['error']}",
        }

    candidate_cols = set(candidate["rows"][0]) if candidate["rows"] else set()
    reference_cols = set(reference["rows"][0]) if reference["rows"] else set()

    if candidate_cols != reference_cols:
        return {
            "passed": False,
            "reason": (
                f"Column names differ. Expected {sorted(reference_cols)}, "
                f"got {sorted(candidate_cols)}."
            ),
        }

    if _normalise(candidate["rows"]) != _normalise(reference["rows"]):
        return {
            "passed": False,
            "reason": (
                f"Rows differ. Expected {reference['row_count']} rows, "
                f"got {candidate['row_count']}, and the values do not match."
            ),
        }

    return {"passed": True, "reason": "Result set matches the reference."}
