from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.analytics import FunnelResponse, KPIResponse, ManagerStatsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/funnel", response_model=FunnelResponse)
async def funnel(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    return await AnalyticsService(session).funnel()


@router.get("/kpi", response_model=KPIResponse)
async def kpi(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    return await AnalyticsService(session).kpi()


@router.get("/manager-stats", response_model=ManagerStatsResponse)
async def manager_stats(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    return await AnalyticsService(session).manager_stats()
