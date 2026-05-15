from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.deal import DealStage


class FunnelStageStats(BaseModel):
    stage: DealStage
    count: int
    total_amount: Decimal


class FunnelResponse(BaseModel):
    stages: list[FunnelStageStats]
    total_deals: int
    total_amount: Decimal


class KPIResponse(BaseModel):
    win_rate: float
    avg_deal_size: Decimal
    avg_cycle_time_days: float | None
    total_won_amount: Decimal
    total_lost_amount: Decimal


class ManagerStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    deals_total: int
    deals_won: int
    deals_lost: int
    revenue: Decimal


class ManagerStatsResponse(BaseModel):
    managers: list[ManagerStats]
