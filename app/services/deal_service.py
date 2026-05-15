"""Deal service with sales-funnel state machine.

This is the refactored, production-quality counterpart to ``bad_deal.py`` —
see ``docs/CODE_REVIEW_REPORT.md`` for the list of issues addressed.
"""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal, DealStage
from app.models.user import User, UserRole
from app.repositories.client_repository import ClientRepository
from app.repositories.deal_repository import DealRepository
from app.schemas.deal import DealCreate, DealUpdate

# Allowed transitions in the sales funnel state machine
FUNNEL_TRANSITIONS: dict[DealStage, set[DealStage]] = {
    DealStage.lead: {DealStage.qualified, DealStage.lost},
    DealStage.qualified: {DealStage.proposal, DealStage.lost},
    DealStage.proposal: {DealStage.negotiation, DealStage.lost},
    DealStage.negotiation: {DealStage.won, DealStage.lost},
    DealStage.won: set(),
    DealStage.lost: set(),
}

# Commission rate tiers — extracted as Decimal constants (no magic numbers, no float)
TIER_LARGE_THRESHOLD = Decimal("1000000")
TIER_MEDIUM_THRESHOLD = Decimal("500000")
COMMISSION_RATE_LARGE = Decimal("0.05")
COMMISSION_RATE_MEDIUM = Decimal("0.08")
COMMISSION_RATE_SMALL = Decimal("0.12")


def calc_commission(amount: Decimal) -> Decimal:
    """Calculate commission using tiered Decimal arithmetic — never float."""
    if amount > TIER_LARGE_THRESHOLD:
        rate = COMMISSION_RATE_LARGE
    elif amount > TIER_MEDIUM_THRESHOLD:
        rate = COMMISSION_RATE_MEDIUM
    else:
        rate = COMMISSION_RATE_SMALL
    return amount * rate


class DealService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DealRepository(session)
        self.client_repo = ClientRepository(session)

    async def list_for_user(
        self,
        user: User,
        stage: DealStage | None = None,
        assigned_to: int | None = None,
    ) -> list[Deal]:
        if user.role == UserRole.sales_rep:
            assigned_to = user.id
        return await self.repo.filter_deals(stage=stage, assigned_to=assigned_to)

    async def get_or_404(self, deal_id: int, user: User) -> Deal:
        deal = await self.repo.get(deal_id)
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        if user.role == UserRole.sales_rep and deal.assigned_to != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your deal")
        return deal

    async def create(self, data: DealCreate, user: User) -> Deal:
        client = await self.client_repo.get(data.client_id)
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        payload = data.model_dump()
        if user.role == UserRole.sales_rep or payload.get("assigned_to") is None:
            payload["assigned_to"] = user.id
        return await self.repo.create(payload)

    async def update(self, deal_id: int, data: DealUpdate, user: User) -> Deal:
        deal = await self.get_or_404(deal_id, user)
        payload = data.model_dump(exclude_unset=True)
        if user.role == UserRole.sales_rep:
            payload.pop("assigned_to", None)
        updated = await self.repo.update(deal.id, payload)
        assert updated is not None
        return updated

    async def transition_stage(self, deal_id: int, new_stage: DealStage, user: User) -> Deal:
        deal = await self.get_or_404(deal_id, user)
        allowed = FUNNEL_TRANSITIONS.get(deal.stage, set())
        if new_stage not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition: {deal.stage.value} -> {new_stage.value}",
            )
        updated = await self.repo.update(deal.id, {"stage": new_stage})
        assert updated is not None
        return updated

    async def delete(self, deal_id: int, user: User) -> None:
        if user.role != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
        ok = await self.repo.delete(deal_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
