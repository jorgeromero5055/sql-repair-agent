"""Run the agent over every generated case and record what happened.

A command, not an endpoint — it takes about half an hour, which no HTTP request survives.

Three things make it survivable on a free tier: it paces itself under the per-minute limit, it
stops cleanly when it reaches a request budget, and it can be resumed, so hitting the daily cap
two-thirds of the way through doesn't waste the day.
"""

import argparse
import time
import uuid
from datetime import datetime, timezone

from google.genai.errors import ClientError

from app.agent.prompt import MODEL
from app.db.models import EvalResult, EvalRun
from app.db.session import SessionLocal
from app.evaluation.corrupt import generate
from app.evaluation.oracle import compare
from app.evaluation.stats import COST_PER_MILLION_TOKENS
from app.repair import repair_with_retries

# The free tier allows 15 a minute, measured as a rolling window rather than a bucket that
# resets. Aiming at 15 means brushing the limit constantly, so aim lower and leave headroom.
REQUESTS_PER_MINUTE = 10

# How long to wait when the limit is hit anyway, and how many times to try again.
RATE_LIMIT_WAIT = 30
RATE_LIMIT_RETRIES = 4


def _pace(requests_used: int, started: float) -> None:
    """Hold back so the run stays under the per-minute limit.

    Going over doesn't slow a request down, it fails it — so the waiting has to be deliberate.
    """
    should_have_taken = requests_used / REQUESTS_PER_MINUTE * 60
    elapsed = time.monotonic() - started

    if should_have_taken > elapsed:
        time.sleep(should_have_taken - elapsed)


def _with_backoff(work):
    """Run something, waiting and retrying if the model says we're going too fast.

    Pacing gets it approximately right; this handles the times it doesn't. A rolling window can
    trip even when the average rate is fine.
    """
    for attempt in range(RATE_LIMIT_RETRIES):
        try:
            return work()
        except ClientError as e:
            last = attempt == RATE_LIMIT_RETRIES - 1
            if e.code != 429 or last:
                raise
            print(f"  rate limited, waiting {RATE_LIMIT_WAIT}s")
            time.sleep(RATE_LIMIT_WAIT)


def _slice(cases: list[dict]) -> list[dict]:
    """One case per break type — the smallest set that still covers every kind of bug.

    The first five cases would all be wrong-table and wrong-column, which is the easy end.
    """
    picked: dict[str, dict] = {}
    for case in cases:
        picked.setdefault(case["break_type"], case)
    return list(picked.values())


def _score(result: dict, case: dict) -> tuple[bool, str | None]:
    """Did the agent's query return the same rows as the one this case was made from?

    Not "did it run" — the agent's own check already asked that, and a query can run and be wrong.
    """
    if not result["fixed_query"]:
        return False, "The agent produced no query."

    verdict = compare(result["fixed_query"], case["reference_sql"])
    return verdict["passed"], None if verdict["passed"] else verdict["reason"]


def _open_run(session, run_id: str | None, note: str | None) -> EvalRun:
    """Continue a run if one was named, otherwise start a new one."""
    if run_id:
        run = session.get(EvalRun, uuid.UUID(run_id))
        if run is None:
            raise SystemExit(f"No run with id {run_id}")
        return run

    run = EvalRun(model=MODEL, note=note)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def run(limit: int | None = None, max_requests: int = 450,
        run_id: str | None = None, note: str | None = None,
        use_slice: bool = False, min_pass: float | None = None) -> None:
    session = SessionLocal()
    cases = generate()

    if use_slice:
        cases = _slice(cases)
    if limit:
        cases = cases[:limit]

    evaluation = _open_run(session, run_id, note)

    # Anything already recorded against this run is skipped, so a stopped run resumes.
    done = {
        row.case_id
        for row in session.query(EvalResult.case_id).filter(
            EvalResult.run_id == evaluation.id
        )
    }

    print(f"run {evaluation.id} — {len(cases) - len(done)} cases to go, model {MODEL}")

    requests_used = evaluation.requests_used
    started = time.monotonic()

    for case in cases:
        if case["id"] in done:
            continue

        if requests_used >= max_requests:
            print(f"stopping: reached the budget of {max_requests} requests")
            break

        _pace(requests_used - evaluation.requests_used, started)

        case_started = time.monotonic()
        result = _with_backoff(
            lambda: repair_with_retries(case["intent"], case["broken_sql"])
        )
        elapsed_ms = int((time.monotonic() - case_started) * 1000)

        passed, reason = _score(result, case)
        turns = sum(a["turns"] for a in result["attempts"])
        requests_used += turns

        session.add(
            EvalResult(
                run_id=evaluation.id,
                case_id=case["id"],
                break_type=case["break_type"],
                passed=passed,
                # pass@1 means right on the first attempt, not right eventually.
                passed_first_try=passed and len(result["attempts"]) == 1,
                attempts=len(result["attempts"]),
                tokens=sum(a["tokens"] for a in result["attempts"]),
                latency_ms=elapsed_ms,
                fixed_query=result["fixed_query"],
                failure_reason=reason,
            )
        )
        evaluation.requests_used = requests_used
        session.commit()

        print(f"  {'PASS' if passed else 'FAIL'}  {case['id']}  "
              f"({len(result['attempts'])} attempts, {turns} requests)")

    evaluation.finished_at = datetime.now(timezone.utc)
    session.commit()

    results = session.query(EvalResult).filter(EvalResult.run_id == evaluation.id).all()
    if results:
        tokens = sum(r.tokens for r in results)
        print(
            f"\n{len(results)} cases · "
            f"pass@1 {sum(r.passed_first_try for r in results) / len(results):.0%} · "
            f"pass@3 {sum(r.passed for r in results) / len(results):.0%} · "
            f"{tokens} tokens · "
            f"${tokens / 1_000_000 * COST_PER_MILLION_TOKENS:.4f} at paid rates"
        )
        print(f"resume with --resume {evaluation.id}")

        # The exit code is what makes this a gate rather than a report.
        pass_rate = sum(r.passed for r in results) / len(results) * 100
        if min_pass is not None and pass_rate < min_pass:
            session.close()
            raise SystemExit(
                f"FAILED: {pass_rate:.0f}% passed, below the floor of {min_pass:.0f}%"
            )

    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the agent over the eval cases.")
    parser.add_argument("--limit", type=int, help="only the first N cases")
    parser.add_argument("--max-requests", type=int, default=450,
                        help="stop after this many model requests (default 450)")
    parser.add_argument("--resume", dest="run_id", help="continue an existing run by id")
    parser.add_argument("--note", help="label this run, e.g. 'before prompt change'")
    parser.add_argument("--slice", action="store_true", dest="use_slice",
                        help="one case per break type, for CI")
    parser.add_argument("--min-pass", type=float,
                        help="exit non-zero if the pass rate is below this")
    args = parser.parse_args()

    run(limit=args.limit, max_requests=args.max_requests,
        run_id=args.run_id, note=args.note,
        use_slice=args.use_slice, min_pass=args.min_pass)
