from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientDetailResponse,
    ClientResponse,
    ClientUpdate,
)
from app.services.client_service import ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/", response_model=list[ClientResponse])
async def list_clients(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ClientService(session).list_for_user(current_user)


@router.get("/search", response_model=list[ClientResponse])
async def search_clients(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ClientService(session).search(q, current_user)


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ClientService(session).create(data, current_user)


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
    client_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ClientService(session).get_or_404(client_id, current_user)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ClientService(session).update(client_id, data, current_user)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await ClientService(session).delete(client_id, current_user)
