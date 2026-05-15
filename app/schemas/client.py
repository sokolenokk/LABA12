from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.client import ClientStatus
from app.schemas.contact import ContactResponse
from app.schemas.deal import DealResponse


class ClientBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    status: ClientStatus = ClientStatus.prospect


class ClientCreate(ClientBase):
    assigned_to: int | None = None


class ClientUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    status: ClientStatus | None = None
    assigned_to: int | None = None


class ClientResponse(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assigned_to: int | None
    created_at: datetime
    updated_at: datetime


class ClientDetailResponse(ClientResponse):
    contacts: list[ContactResponse] = []
    deals: list[DealResponse] = []
