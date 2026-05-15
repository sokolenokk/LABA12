from sqlalchemy import or_, select

from app.models.client import Client
from app.repositories.base_repository import BaseRepository


class ClientRepository(BaseRepository[Client]):
    model = Client

    async def get_by_manager_id(self, user_id: int) -> list[Client]:
        stmt = select(Client).where(Client.assigned_to == user_id).order_by(Client.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(self, query: str) -> list[Client]:
        pattern = f"%{query}%"
        stmt = (
            select(Client)
            .where(
                or_(
                    Client.company_name.ilike(pattern),
                    Client.contact_person.ilike(pattern),
                )
            )
            .order_by(Client.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
