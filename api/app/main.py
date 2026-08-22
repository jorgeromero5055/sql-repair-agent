from fastapi import Depends, FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid


from app.db.models import Repair
from app.db.session import get_session
from app.schemas import RepairCreate, RepairOut,RepairListItem
from app.worker import handler as worker_handler

import json
import os

import boto3

app = FastAPI()

sqs = boto3.client("sqs")
QUEUE_URL = os.environ["QUEUE_URL"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://d2ikqw86csxqqd.cloudfront.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": 2}

@app.post("/repairs", response_model=RepairOut, status_code=201)
def create_repair(body: RepairCreate, session: Session = Depends(get_session)):
    repair = Repair(intent=body.intent, broken_query=body.broken_query)
    session.add(repair)
    session.commit()
    session.refresh(repair)

    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps({"repair_id": str(repair.id)}),
    )

    return repair

@app.post("/events")
def events(event: dict):
    return worker_handler(event, None)

@app.get("/repairs", response_model=list[RepairListItem])
def list_repairs(session: Session = Depends(get_session)):
    return (
        session.query(Repair)
        .order_by(Repair.created_at.desc())
        .limit(50)
        .all()
    )

@app.get("/repairs/{repair_id}", response_model=RepairOut)
def get_repair(repair_id: uuid.UUID, session: Session = Depends(get_session)):
    repair = session.get(Repair, repair_id)
    if repair is None:
        raise HTTPException(status_code=404, detail="repair not found")
    return repair