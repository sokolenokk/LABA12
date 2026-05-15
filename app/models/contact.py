from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client


class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    position: Mapped[str | None] = mapped_column(sa.String(150), nullable=True)
    is_primary: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    client_id: Mapped[int] = mapped_column(
        sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    client: Mapped["Client"] = relationship(back_populates="contacts", lazy="selectin")
