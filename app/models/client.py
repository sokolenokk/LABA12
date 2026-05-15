import enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.deal import Deal
    from app.models.task import Task
    from app.models.user import User


class ClientStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    prospect = "prospect"
    archived = "archived"


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(
        sa.String(255), index=True, nullable=False
    )
    contact_person: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    status: Mapped[ClientStatus] = mapped_column(
        sa.Enum(ClientStatus, name="client_status"),
        nullable=False,
        default=ClientStatus.prospect,
    )
    assigned_to: Mapped[int | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    assigned_user: Mapped["User | None"] = relationship(
        back_populates="clients", lazy="selectin", foreign_keys=[assigned_to]
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="client", lazy="selectin", cascade="all, delete-orphan"
    )
    deals: Mapped[list["Deal"]] = relationship(
        back_populates="client", lazy="selectin", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="client", lazy="selectin")
