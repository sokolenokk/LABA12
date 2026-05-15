from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal, DealStage
from app.models.user import User
from app.schemas.analytics import (
    FunnelResponse,
    FunnelStageStats,
    KPIResponse,
    ManagerStats,
    ManagerStatsResponse,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def funnel(self) -> FunnelResponse:
        stmt = select(
            Deal.stage,
            func.count(Deal.id).label("count"),
            func.coalesce(func.sum(Deal.amount), 0).label("total"),
        ).group_by(Deal.stage)
        result = await self.session.execute(stmt)
        rows = {row.stage: (row.count, Decimal(str(row.total))) for row in result.all()}

        stages: list[FunnelStageStats] = []
        total_deals = 0
        total_amount = Decimal("0")
        for stage in DealStage:
            count, amount = rows.get(stage, (0, Decimal("0")))
            stages.append(FunnelStageStats(stage=stage, count=count, total_amount=amount))
            total_deals += count
            total_amount += amount
        return FunnelResponse(
            stages=stages, total_deals=total_deals, total_amount=total_amount
        )

    async def kpi(self) -> KPIResponse:
        won_stmt = select(
            func.count(Deal.id), func.coalesce(func.sum(Deal.amount), 0)
        ).where(Deal.stage == DealStage.won)
        lost_stmt = select(
            func.count(Deal.id), func.coalesce(func.sum(Deal.amount), 0)
        ).where(Deal.stage == DealStage.lost)
        all_stmt = select(
            func.count(Deal.id), func.coalesce(func.avg(Deal.amount), 0)
        )

        won_count, won_amount = (await self.session.execute(won_stmt)).one()
        lost_count, lost_amount = (await self.session.execute(lost_stmt)).one()
        total_count, avg_amount = (await self.session.execute(all_stmt)).one()

        closed = won_count + lost_count
        win_rate = (won_count / closed) if closed > 0 else 0.0

        cycle_stmt = select(
            func.avg(
                func.julianday(Deal.updated_at) - func.julianday(Deal.created_at)
            )
        ).where(Deal.stage == DealStage.won)
        try:
            avg_cycle = (await self.session.execute(cycle_stmt)).scalar()
            avg_cycle_days = float(avg_cycle) if avg_cycle is not None else None
        except Exception:
            avg_cycle_days = None

        return KPIResponse(
            win_rate=win_rate,
            avg_deal_size=Decimal(str(avg_amount)) if total_count else Decimal("0"),
            avg_cycle_time_days=avg_cycle_days,
            total_won_amount=Decimal(str(won_amount)),
            total_lost_amount=Decimal(str(lost_amount)),
        )

    async def manager_stats(self) -> ManagerStatsResponse:
        stmt = (
            select(
                User.id,
                User.full_name,
                func.count(Deal.id).label("total"),
                func.sum(case((Deal.stage == DealStage.won, 1), else_=0)).label("won"),
                func.sum(case((Deal.stage == DealStage.lost, 1), else_=0)).label("lost"),
                func.coalesce(
                    func.sum(case((Deal.stage == DealStage.won, Deal.amount), else_=0)),
                    0,
                ).label("revenue"),
            )
            .join(Deal, Deal.assigned_to == User.id, isouter=True)
            .group_by(User.id, User.full_name)
            .order_by(User.id)
        )
        result = await self.session.execute(stmt)
        managers = [
            ManagerStats(
                user_id=row.id,
                full_name=row.full_name,
                deals_total=row.total or 0,
                deals_won=row.won or 0,
                deals_lost=row.lost or 0,
                revenue=Decimal(str(row.revenue or 0)),
            )
            for row in result.all()
        ]
        return ManagerStatsResponse(managers=managers)
