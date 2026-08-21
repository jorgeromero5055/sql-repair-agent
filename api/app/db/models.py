import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RepairStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    needs_review = "needs_review"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"


class Repair(Base):
    __tablename__ = "repairs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    broken_query: Mapped[str] = mapped_column(Text, nullable=False)
    fixed_query: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RepairStatus] = mapped_column(
        Enum(RepairStatus, name="repair_status"),
        nullable=False,
        default=RepairStatus.queued,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repair_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repairs.id", ondelete="CASCADE"), nullable=False
    )
    attempts: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())