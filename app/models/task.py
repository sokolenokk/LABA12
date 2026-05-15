import enum
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.deal import Deal
    from app.models.user import User


class TaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskType(str, enum.Enum):
    call = "call"
    meeting = "meeting"
    email = "email"
    follow_up = "follow_up"
    other = "other"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        sa.Enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.medium,
    )
    status: Mapped[TaskStatus] = mapped_column(
        sa.Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.pending,
        index=True,
    )
    task_type: Mapped[TaskType] = mapped_column(
        sa.Enum(TaskType, name="task_type"),
        nullable=False,
        default=TaskType.other,
    )

    assigned_to: Mapped[int | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    deal_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True
    )

    assigned_user: Mapped["User | None"] = relationship(
        back_populates="tasks", lazy="selectin", foreign_keys=[assigned_to]
    )
    client: Mapped["Client | None"] = relationship(
        back_populates="tasks", lazy="selectin"
    )
    deal: Mapped["Deal | None"] = relationship(back_populates="tasks", lazy="selectin")
