import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RepairStatus


class RepairCreate(BaseModel):
    intent: str = Field(min_length=1, max_length=1000)
    broken_query: str = Field(min_length=1, max_length=10000)


class RepairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    intent: str
    broken_query: str
    fixed_query: str | None
    status: RepairStatus
    created_at: datetime
    updated_at: datetime