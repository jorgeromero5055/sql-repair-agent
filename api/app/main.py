import json
import uuid

import boto3
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import config
from app.approval import NotReviewable, approve, reject
from app.db.models import EvalResult, EvalRun, Repair, Trace
from app.db.session import get_session
from app.evaluation.stats import by_break_type, summarise
from app.review import group_attempts, preview_rows
from app.schemas import (
    RepairCreate,
    RepairDetail,
    RepairListItem,
    RepairOut,
    RepairReject,
    RunDetail,
    RunSummary,
    SavedQueryOut,
    TraceOut,
)
from app.worker import handler as worker_handler

app = FastAPI()

sqs = boto3.client("sqs")
QUEUE_URL = config.QUEUE_URL

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


@app.get("/repairs/{repair_id}", response_model=RepairDetail)
def get_repair(repair_id: uuid.UUID, session: Session = Depends(get_session)):
    repair = session.get(Repair, repair_id)
    if repair is None:
        raise HTTPException(status_code=404, detail="repair not found")

    # A retried queue message can leave a second trace behind. The newest is the real one.
    trace = (
        session.query(Trace)
        .filter(Trace.repair_id == repair.id)
        .order_by(Trace.created_at.desc())
        .first()
    )

    return RepairDetail(
        **RepairOut.model_validate(repair).model_dump(),
        trace=TraceOut.model_validate(trace) if trace else None,
        attempts=group_attempts(trace),
        preview=preview_rows(repair),
    )


@app.post("/repairs/{repair_id}/approve", response_model=SavedQueryOut, status_code=201)
def approve_repair(repair_id: uuid.UUID, session: Session = Depends(get_session)):
    repair = session.get(Repair, repair_id)
    if repair is None:
        raise HTTPException(status_code=404, detail="repair not found")

    try:
        return approve(repair, session)
    except NotReviewable as e:
        # 409: it exists, but it's in the wrong state for this.
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/repairs/{repair_id}/reject", response_model=RepairOut)
def reject_repair(
    repair_id: uuid.UUID,
    body: RepairReject,
    session: Session = Depends(get_session),
):
    repair = session.get(Repair, repair_id)
    if repair is None:
        raise HTTPException(status_code=404, detail="repair not found")

    try:
        return reject(repair, session, body.reason)
    except NotReviewable as e:
        # 409: it exists, but it's in the wrong state for this.
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/runs", response_model=list[RunSummary])
def list_runs(session: Session = Depends(get_session)):
    runs = session.query(EvalRun).order_by(EvalRun.started_at.desc()).limit(20).all()

    # The numbers are worked out here rather than stored - the results are the record.
    return [
        summarise(
            run,
            session.query(EvalResult).filter(EvalResult.run_id == run.id).all(),
        )
        for run in runs
    ]


@app.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: uuid.UUID, session: Session = Depends(get_session)):
    run = session.get(EvalRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    results = session.query(EvalResult).filter(EvalResult.run_id == run.id).all()

    return RunDetail(
        **summarise(run, results),
        by_break_type=by_break_type(results),
        # A pass rate says something is wrong; only these say what.
        failures=[r for r in results if not r.passed],
    )
