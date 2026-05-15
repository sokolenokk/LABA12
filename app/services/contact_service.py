from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.user import User, UserRole
from app.repositories.client_repository import ClientRepository
from app.repositories.contact_repository import ContactRepository
from app.schemas.contact import ContactCreate, ContactUpdate


class ContactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ContactRepository(session)
        self.client_repo = ClientRepository(session)

    async def list_contacts(self, user: User, client_id: int | None = None) -> list[Contact]:
        if client_id is not None:
            await self._ensure_client_access(client_id, user)
            return await self.repo.get_by_client_id(client_id)
        contacts = await self.repo.get_multi(skip=0, limit=1000)
        if user.role == UserRole.sales_rep:
            allowed_clients = {
                c.id
                for c in await ClientRepository(self.session).get_by_manager_id(user.id)
            }
            return [c for c in contacts if c.client_id in allowed_clients]
        return contacts

    async def create(self, data: ContactCreate, user: User) -> Contact:
        await self._ensure_client_access(data.client_id, user)
        return await self.repo.create(data.model_dump())

    async def update(self, contact_id: int, data: ContactUpdate, user: User) -> Contact:
        contact = await self.repo.get(contact_id)
        if contact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        await self._ensure_client_access(contact.client_id, user)
        updated = await self.repo.update(contact_id, data.model_dump(exclude_unset=True))
        assert updated is not None
        return updated

    async def delete(self, contact_id: int, user: User) -> None:
        if user.role != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
        ok = await self.repo.delete(contact_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    async def _ensure_client_access(self, client_id: int, user: User) -> None:
        client = await self.client_repo.get(client_id)
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        if user.role == UserRole.sales_rep and client.assigned_to != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your client")
