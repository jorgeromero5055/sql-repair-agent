import json
import time
import uuid

from app.db.models import Repair, RepairStatus, Trace
from app.db.session import SessionLocal

from app.agent.loop import repair as run_agent

MAX_ATTEMPTS = 3


def process(repair_id: uuid.UUID, attempt: int = 1) -> None:
    started = time.monotonic()
    session = SessionLocal()
    try:
        repair = session.get(Repair, repair_id)
        if repair is None:
            print(f"repair {repair_id} not found, dropping message")
            return

        try:
            repair.status = RepairStatus.running
            session.commit()

            result = run_agent(repair.intent, repair.broken_query)

            repair.fixed_query = result["fixed_query"]
            repair.explanation = result["explanation"]
            repair.status = RepairStatus.needs_review
            session.commit()

            print(
                f"repair {repair_id} -> needs_review "
                f"(attempt {attempt}, {result['turns']} turns, "
                f"converged={result['converged']})"
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
        session.add(
            Trace(repair_id=repair_id, attempts=attempt, latency_ms=elapsed_ms)
        )
        session.commit()
        session.close()


def handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        attempt = int(record.get("attributes", {}).get("ApproximateReceiveCount", 1))
        process(uuid.UUID(body["repair_id"]), attempt)
    return {"ok": True}