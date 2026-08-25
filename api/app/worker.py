import json
import time
import uuid

from app.db.models import Repair, RepairStatus, Trace
from app.db.session import SessionLocal
from app.repair import repair_with_retries

MAX_ATTEMPTS = 3


def process(repair_id: uuid.UUID, attempt: int = 1) -> None:
    started = time.monotonic()
    trace_data: dict = {}
    session = SessionLocal()

    try:
        repair = session.get(Repair, repair_id)
        if repair is None:
            print(f"repair {repair_id} not found, dropping message")
            return

        try:
            repair.status = RepairStatus.running
            session.commit()

            trace_data = repair_with_retries(repair.intent, repair.broken_query)

            repair.fixed_query = trace_data["fixed_query"]
            repair.explanation = trace_data["explanation"]
            repair.status = (
                RepairStatus.needs_review
                if trace_data["passed"]
                else RepairStatus.failed
            )
            session.commit()

            print(
                f"repair {repair_id} -> {repair.status.value} "
                f"({len(trace_data['attempts'])} attempts)"
            )

        except Exception:
            session.rollback()
            if attempt >= MAX_ATTEMPTS:
                repair.status = RepairStatus.failed
                session.commit()
                print(f"repair {repair_id} -> failed after {attempt} attempts")
            raise

    finally:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        runs = trace_data.get("attempts", [])

        statements = [
            {
                "attempt": run["attempt"],
                "attempt_passed": run["passed"],
                "attempt_reason": run["reason"],
                **statement,
            }
            for run in runs
            for statement in run["statements"]
        ]

        session.add(
            Trace(
                repair_id=repair_id,
                attempts=len(runs),
                turns=sum(run["turns"] for run in runs),
                tokens=sum(run["tokens"] for run in runs),
                passed=bool(trace_data.get("passed")),
                failure_reason=(
                    None if trace_data.get("passed") else runs[-1]["reason"] if runs else None
                ),
                statements=statements or None,
                latency_ms=elapsed_ms,
            )
        )
        session.commit()
        session.close()


def handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        attempt = int(record.get("attributes", {}).get("ApproximateReceiveCount", 1))
        process(uuid.UUID(body["repair_id"]), attempt)
    return {"ok": True}