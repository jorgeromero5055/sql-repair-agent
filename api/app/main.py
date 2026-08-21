from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.models import Repair
from app.db.session import get_session
from app.schemas import RepairCreate, RepairOut

app = FastAPI()

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
    return repair