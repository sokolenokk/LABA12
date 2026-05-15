from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.user import User, UserRole
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate, ClientUpdate


class ClientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ClientRepository(session)

    async def list_for_user(self, user: User) -> list[Client]:
        if user.role in (UserRole.admin, UserRole.manager):
            return await self.repo.get_multi(skip=0, limit=1000)
        return await self.repo.get_by_manager_id(user.id)

    async def search(self, query: str, user: User) -> list[Client]:
        results = await self.repo.search(query)
        if user.role == UserRole.sales_rep:
            return [c for c in results if c.assigned_to == user.id]
        return results

    async def get_or_404(self, client_id: int, user: User) -> Client:
        client = await self.repo.get(client_id)
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
            )
        if user.role == UserRole.sales_rep and client.assigned_to != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not your client"
            )
        return client

    async def create(self, data: ClientCreate, user: User) -> Client:
        payload = data.model_dump()
        if user.role == UserRole.sales_rep or payload.get("assigned_to") is None:
            payload["assigned_to"] = user.id
        return await self.repo.create(payload)

    async def update(self, client_id: int, data: ClientUpdate, user: User) -> Client:
        client = await self.get_or_404(client_id, user)
        if user.role == UserRole.sales_rep and client.assigned_to != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not your client"
            )
        payload = data.model_dump(exclude_unset=True)
        if user.role == UserRole.sales_rep:
            payload.pop("assigned_to", None)
        updated = await self.repo.update(client_id, payload)
        assert updated is not None
        return updated

    async def delete(self, client_id: int, user: User) -> None:
        if user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin only"
            )
        ok = await self.repo.delete(client_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
            )
