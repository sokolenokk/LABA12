from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.deal import DealStage


class DealBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=2)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    probability: int = Field(default=0, ge=0, le=100)
    expected_close_date: date | None = None
    notes: str | None = None


class DealCreate(DealBase):
    client_id: int
    assigned_to: int | None = None
    stage: DealStage = DealStage.lead


class DealUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    notes: str | None = None
    assigned_to: int | None = None


class DealStageUpdate(BaseModel):
    stage: DealStage


class DealResponse(DealBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: DealStage
    client_id: int
    assigned_to: int | None
    created_at: datetime
    updated_at: datetime
