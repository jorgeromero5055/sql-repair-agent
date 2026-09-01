import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RepairStatus


class RepairCreate(BaseModel):
    intent: str = Field(min_length=1, max_length=1000)
    broken_query: str = Field(min_length=1, max_length=10000)


class RepairReject(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class RepairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    intent: str
    broken_query: str
    fixed_query: str | None
    explanation: str | None
    status: RepairStatus
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class RepairListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    intent: str
    status: RepairStatus
    created_at: datetime


class SavedQueryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repair_id: uuid.UUID
    sql: str
    result_preview: list[dict] | None
    created_at: datetime


class AttemptOut(BaseModel):
    attempt: int
    passed: bool
    reason: str | None
    statements: list[dict]


class TraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempts: int
    turns: int
    tokens: int
    passed: bool
    failure_reason: str | None
    latency_ms: int | None


class RepairDetail(RepairOut):
    """RepairOut plus everything the review screen needs."""

    trace: TraceOut | None
    attempts: list[AttemptOut]
    preview: list[dict] | None

