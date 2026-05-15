from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.deal import DealStage
from app.models.user import User
from app.schemas.deal import DealCreate, DealResponse, DealStageUpdate, DealUpdate
from app.services.deal_service import DealService

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("/", response_model=list[DealResponse])
async def list_deals(
    stage: DealStage | None = Query(default=None),
    assigned_to: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DealService(session).list_for_user(current_user, stage=stage, assigned_to=assigned_to)


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    data: DealCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DealService(session).create(data, current_user)


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DealService(session).get_or_404(deal_id, current_user)


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    data: DealUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DealService(session).update(deal_id, data, current_user)


@router.patch("/{deal_id}/stage", response_model=DealResponse)
async def change_stage(
    deal_id: int,
    data: DealStageUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DealService(session).transition_stage(deal_id, data.stage, current_user)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await DealService(session).delete(deal_id, current_user)
