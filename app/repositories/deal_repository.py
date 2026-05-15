from sqlalchemy import select

from app.models.deal import Deal, DealStage
from app.repositories.base_repository import BaseRepository


class DealRepository(BaseRepository[Deal]):
    model = Deal

    async def get_by_assigned_user(self, user_id: int) -> list[Deal]:
        stmt = select(Deal).where(Deal.assigned_to == user_id).order_by(Deal.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_stage(self, stage: DealStage) -> list[Deal]:
        stmt = select(Deal).where(Deal.stage == stage).order_by(Deal.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def filter_deals(
        self,
        stage: DealStage | None = None,
        assigned_to: int | None = None,
    ) -> list[Deal]:
        stmt = select(Deal)
        if stage is not None:
            stmt = stmt.where(Deal.stage == stage)
        if assigned_to is not None:
            stmt = stmt.where(Deal.assigned_to == assigned_to)
        stmt = stmt.order_by(Deal.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
