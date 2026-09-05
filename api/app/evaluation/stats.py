"""Arithmetic over eval results.

Nothing here is stored. The results are the record; these numbers are a view of them, worked out
whenever someone asks. Storing a pass rate would mean two versions of the truth that can disagree.

Both the runner and the API use this, so the cost rate lives in one place.
"""

# What the tokens would cost off the free tier. Real cost today is zero.
COST_PER_MILLION_TOKENS = 0.10


def _percent(count: int, total: int) -> float:
    return round(count / total * 100, 1) if total else 0.0


def summarise(run, results: list) -> dict:
    """A run's headline numbers."""
    total = len(results)
    tokens = sum(r.tokens for r in results)
    timed = [r.latency_ms for r in results if r.latency_ms is not None]

    return {
        "id": run.id,
        "note": run.note,
        "model": run.model,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "cases": total,
        "pass_at_1": _percent(sum(1 for r in results if r.passed_first_try), total),
        "pass_at_3": _percent(sum(1 for r in results if r.passed), total),
        "avg_attempts": round(sum(r.attempts for r in results) / total, 2) if total else 0.0,
        "avg_latency_ms": round(sum(timed) / len(timed)) if timed else None,
        "tokens": tokens,
        "cost_usd": round(tokens / 1_000_000 * COST_PER_MILLION_TOKENS, 4),
    }


def by_break_type(results: list) -> list[dict]:
    """The same pass rate, split by which kind of break it was.

    This is where the headline number gives itself away — most cases are the easy kinds.
    """
    groups: dict[str, list] = {}
    for result in results:
        groups.setdefault(result.break_type, []).append(result)

    return [
        {
            "break_type": name,
            "cases": len(rows),
            "pass_at_1": _percent(sum(1 for r in rows if r.passed_first_try), len(rows)),
            "pass_at_3": _percent(sum(1 for r in rows if r.passed), len(rows)),
        }
        for name, rows in sorted(groups.items())
    ]
