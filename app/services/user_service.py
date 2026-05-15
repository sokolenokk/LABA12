from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def list_users(self) -> list[User]:
        return await self.repo.get_multi(skip=0, limit=1000)

    async def get_or_404(self, user_id: int) -> User:
        user = await self.repo.get(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def deactivate(self, user_id: int) -> User:
        user = await self.get_or_404(user_id)
        updated = await self.repo.update(user.id, {"is_active": False})
        assert updated is not None
        return updated
