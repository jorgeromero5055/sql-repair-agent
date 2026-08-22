import json
import uuid

from app.db.models import Repair, RepairStatus
from app.db.session import SessionLocal


def process(repair_id: uuid.UUID) -> None:
    session = SessionLocal()
    try:
        repair = session.get(Repair, repair_id)
        if repair is None:
            print(f"repair {repair_id} not found, dropping message")
            return

        repair.status = RepairStatus.running
        session.commit()

        repair.fixed_query = "-- canned result, the agent arrives in v2\nselect 1"
        repair.status = RepairStatus.needs_review
        session.commit()

        print(f"repair {repair_id} -> needs_review")
    finally:
        session.close()


def handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        process(uuid.UUID(body["repair_id"]))
    return {"ok": True}