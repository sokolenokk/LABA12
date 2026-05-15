from sqlalchemy import select

from app.models.contact import Contact
from app.repositories.base_repository import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    model = Contact

    async def get_by_client_id(self, client_id: int) -> list[Contact]:
        stmt = (
            select(Contact).where(Contact.client_id == client_id).order_by(Contact.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
