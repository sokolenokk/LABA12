import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.task import Task
    from app.models.user import User


class DealStage(str, enum.Enum):
    lead = "lead"
    qualified = "qualified"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class Deal(Base, TimestampMixin):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False, default="RUB")
    stage: Mapped[DealStage] = mapped_column(
        sa.Enum(DealStage, name="deal_stage"),
        nullable=False,
        default=DealStage.lead,
        index=True,
    )
    probability: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    expected_close_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    client_id: Mapped[int] = mapped_column(
        sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    client: Mapped["Client"] = relationship(back_populates="deals", lazy="selectin")
    assigned_user: Mapped["User | None"] = relationship(
        back_populates="deals", lazy="selectin", foreign_keys=[assigned_to]
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="deal", lazy="selectin")
