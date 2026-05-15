import enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.deal import Deal
    from app.models.task import Task


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    sales_rep = "sales_rep"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        sa.String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="user_role"), nullable=False, default=UserRole.sales_rep
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    clients: Mapped[list["Client"]] = relationship(
        back_populates="assigned_user",
        lazy="selectin",
        foreign_keys="Client.assigned_to",
    )
    deals: Mapped[list["Deal"]] = relationship(
        back_populates="assigned_user", lazy="selectin", foreign_keys="Deal.assigned_to"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="assigned_user", lazy="selectin", foreign_keys="Task.assigned_to"
    )
