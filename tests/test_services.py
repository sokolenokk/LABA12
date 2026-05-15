"""Unit tests calling services directly (no HTTP layer).

These tests increase coverage of services and repositories by exercising
code paths that are hard to reach through the API.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.client import Client, ClientStatus
from app.models.deal import Deal, DealStage
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.repositories.client_repository import ClientRepository
from app.repositories.deal_repository import DealRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegister
from app.schemas.client import ClientCreate
from app.schemas.deal import DealCreate
from app.schemas.task import TaskCreate
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.client_service import ClientService
from app.services.deal_service import (
    COMMISSION_RATE_LARGE,
    COMMISSION_RATE_MEDIUM,
    COMMISSION_RATE_SMALL,
    FUNNEL_TRANSITIONS,
    DealService,
    calc_commission,
)
from app.services.task_service import TaskService
from app.services.user_service import UserService


# ---------- helpers ----------


async def _make_user(
    session, email="u@test.com", role=UserRole.sales_rep, full_name="U"
) -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Strong123!"),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


# ---------- calc_commission (pure function, no DB) ----------


def test_calc_commission_small_tier():
    result = calc_commission(Decimal("100"))
    assert result == Decimal("100") * COMMISSION_RATE_SMALL


def test_calc_commission_medium_tier():
    result = calc_commission(Decimal("700000"))
    assert result == Decimal("700000") * COMMISSION_RATE_MEDIUM


def test_calc_commission_large_tier():
    result = calc_commission(Decimal("2000000"))
    assert result == Decimal("2000000") * COMMISSION_RATE_LARGE


def test_calc_commission_returns_decimal():
    result = calc_commission(Decimal("123.45"))
    assert isinstance(result, Decimal)


def test_funnel_transitions_terminal_states():
    assert FUNNEL_TRANSITIONS[DealStage.won] == set()
    assert FUNNEL_TRANSITIONS[DealStage.lost] == set()


# ---------- AuthService ----------


@pytest.mark.asyncio
async def test_auth_service_register_and_authenticate(session):
    auth = AuthService(session)
    user = await auth.register(
        UserRegister(
            email="svc@test.com",
            password="Strong123!",
            full_name="Svc",
            role=UserRole.sales_rep,
        )
    )
    assert user.id is not None
    token = await auth.authenticate("svc@test.com", "Strong123!")
    assert isinstance(token, str) and len(token) > 20


@pytest.mark.asyncio
async def test_auth_service_register_duplicate(session):
    auth = AuthService(session)
    payload = UserRegister(
        email="dup@test.com",
        password="Strong123!",
        full_name="D",
        role=UserRole.sales_rep,
    )
    await auth.register(payload)
    with pytest.raises(HTTPException) as exc:
        await auth.register(payload)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_service_authenticate_wrong_password(session):
    auth = AuthService(session)
    await auth.register(
        UserRegister(
            email="x@test.com",
            password="Strong123!",
            full_name="X",
            role=UserRole.sales_rep,
        )
    )
    with pytest.raises(HTTPException) as exc:
        await auth.authenticate("x@test.com", "WrongPassword")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_service_authenticate_inactive_user(session):
    auth = AuthService(session)
    user = await auth.register(
        UserRegister(
            email="inactive@test.com",
            password="Strong123!",
            full_name="I",
            role=UserRole.sales_rep,
        )
    )
    user.is_active = False
    await session.flush()
    with pytest.raises(HTTPException) as exc:
        await auth.authenticate("inactive@test.com", "Strong123!")
    assert exc.value.status_code == 401


# ---------- ClientService ----------


@pytest.mark.asyncio
async def test_client_service_search_filters_for_sales_rep(session):
    rep = await _make_user(session, email="rep1@test.com", role=UserRole.sales_rep)
    other = await _make_user(session, email="rep2@test.com", role=UserRole.sales_rep)
    repo = ClientRepository(session)
    await repo.create(
        {"company_name": "Acme Foo", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await repo.create(
        {
            "company_name": "Acme Bar",
            "assigned_to": other.id,
            "status": ClientStatus.active,
        }
    )
    await session.flush()
    service = ClientService(session)
    rep_results = await service.search("acme", rep)
    assert len(rep_results) == 1
    assert rep_results[0].company_name == "Acme Foo"


@pytest.mark.asyncio
async def test_client_service_sales_rep_cannot_steal_assignment(session):
    rep = await _make_user(session, email="rep3@test.com", role=UserRole.sales_rep)
    other = await _make_user(session, email="rep4@test.com", role=UserRole.sales_rep)
    service = ClientService(session)
    # sales_rep tries to assign client to someone else — must be ignored
    created = await service.create(
        ClientCreate(company_name="Mine", assigned_to=other.id), rep
    )
    assert created.assigned_to == rep.id


@pytest.mark.asyncio
async def test_client_service_delete_missing(session):
    admin = await _make_user(session, email="adm@test.com", role=UserRole.admin)
    service = ClientService(session)
    with pytest.raises(HTTPException) as exc:
        await service.delete(99999, admin)
    assert exc.value.status_code == 404


# ---------- DealService ----------


@pytest.mark.asyncio
async def test_deal_service_full_funnel(session):
    rep = await _make_user(session, email="dealrep@test.com")
    client_repo = ClientRepository(session)
    client = await client_repo.create(
        {"company_name": "C", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await session.flush()
    service = DealService(session)
    deal = await service.create(
        DealCreate(
            title="D",
            amount=Decimal("100.00"),
            client_id=client.id,
            stage=DealStage.lead,
        ),
        rep,
    )
    for stage in [
        DealStage.qualified,
        DealStage.proposal,
        DealStage.negotiation,
        DealStage.won,
    ]:
        deal = await service.transition_stage(deal.id, stage, rep)
        assert deal.stage == stage


@pytest.mark.asyncio
async def test_deal_service_invalid_transition(session):
    rep = await _make_user(session, email="bad@test.com")
    client = await ClientRepository(session).create(
        {"company_name": "C", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await session.flush()
    service = DealService(session)
    deal = await service.create(
        DealCreate(
            title="D",
            amount=Decimal("100"),
            client_id=client.id,
            stage=DealStage.lead,
        ),
        rep,
    )
    with pytest.raises(HTTPException) as exc:
        await service.transition_stage(deal.id, DealStage.won, rep)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_deal_service_get_404(session):
    rep = await _make_user(session, email="ghost@test.com")
    service = DealService(session)
    with pytest.raises(HTTPException) as exc:
        await service.get_or_404(9999, rep)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_deal_service_create_missing_client(session):
    rep = await _make_user(session, email="nc@test.com")
    service = DealService(session)
    with pytest.raises(HTTPException) as exc:
        await service.create(
            DealCreate(title="X", amount=Decimal("100"), client_id=99999), rep
        )
    assert exc.value.status_code == 404


# ---------- TaskService ----------


@pytest.mark.asyncio
async def test_task_service_overdue_filters_completed(session):
    rep = await _make_user(session, email="tsk@test.com")
    repo = TaskRepository(session)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    await repo.create(
        {
            "title": "Overdue pending",
            "due_date": past,
            "status": TaskStatus.pending,
            "assigned_to": rep.id,
        }
    )
    await repo.create(
        {
            "title": "Overdue completed",
            "due_date": past,
            "status": TaskStatus.completed,
            "assigned_to": rep.id,
        }
    )
    await session.flush()
    service = TaskService(session)
    overdue = await service.list_overdue(rep)
    assert len(overdue) == 1
    assert overdue[0].title == "Overdue pending"


@pytest.mark.asyncio
async def test_task_service_manager_sees_all_overdue(session):
    rep = await _make_user(session, email="trep@test.com")
    manager = await _make_user(session, email="tmgr@test.com", role=UserRole.manager)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    await TaskRepository(session).create(
        {
            "title": "Foreign overdue",
            "due_date": past,
            "status": TaskStatus.pending,
            "assigned_to": rep.id,
        }
    )
    await session.flush()
    service = TaskService(session)
    overdue = await service.list_overdue(manager)
    assert len(overdue) == 1


# ---------- UserService ----------


@pytest.mark.asyncio
async def test_user_service_deactivate(session):
    user = await _make_user(session, email="de@test.com")
    service = UserService(session)
    result = await service.deactivate(user.id)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_user_service_get_404(session):
    service = UserService(session)
    with pytest.raises(HTTPException) as exc:
        await service.get_or_404(99999)
    assert exc.value.status_code == 404


# ---------- AnalyticsService ----------


@pytest.mark.asyncio
async def test_analytics_funnel_empty(session):
    service = AnalyticsService(session)
    result = await service.funnel()
    assert result.total_deals == 0
    assert {s.stage for s in result.stages} == set(DealStage)


@pytest.mark.asyncio
async def test_analytics_kpi_with_won_and_lost(session):
    rep = await _make_user(session, email="kpi@test.com")
    client = await ClientRepository(session).create(
        {"company_name": "C", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await session.flush()
    repo = DealRepository(session)
    await repo.create(
        {
            "title": "Won",
            "amount": Decimal("1000"),
            "client_id": client.id,
            "assigned_to": rep.id,
            "stage": DealStage.won,
        }
    )
    await repo.create(
        {
            "title": "Lost",
            "amount": Decimal("500"),
            "client_id": client.id,
            "assigned_to": rep.id,
            "stage": DealStage.lost,
        }
    )
    await session.flush()
    service = AnalyticsService(session)
    kpi = await service.kpi()
    assert kpi.win_rate == 0.5
    assert kpi.total_won_amount == Decimal("1000")


@pytest.mark.asyncio
async def test_analytics_manager_stats(session):
    rep = await _make_user(session, email="ms@test.com")
    client = await ClientRepository(session).create(
        {"company_name": "C", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await session.flush()
    await DealRepository(session).create(
        {
            "title": "W",
            "amount": Decimal("100"),
            "client_id": client.id,
            "assigned_to": rep.id,
            "stage": DealStage.won,
        }
    )
    await session.flush()
    service = AnalyticsService(session)
    result = await service.manager_stats()
    assert len(result.managers) >= 1
    assert any(m.deals_won >= 1 for m in result.managers)


# ---------- Repositories (extra coverage) ----------


@pytest.mark.asyncio
async def test_user_repository_get_by_email(session):
    repo = UserRepository(session)
    await _make_user(session, email="findme@test.com")
    found = await repo.get_by_email("findme@test.com")
    assert found is not None
    assert found.email == "findme@test.com"
    missing = await repo.get_by_email("nope@test.com")
    assert missing is None


@pytest.mark.asyncio
async def test_deal_repository_filter_by_assigned(session):
    rep = await _make_user(session, email="dr@test.com")
    client = await ClientRepository(session).create(
        {"company_name": "C", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await session.flush()
    repo = DealRepository(session)
    await repo.create(
        {
            "title": "D",
            "amount": Decimal("1"),
            "client_id": client.id,
            "assigned_to": rep.id,
            "stage": DealStage.lead,
        }
    )
    await session.flush()
    results = await repo.get_by_assigned_user(rep.id)
    assert len(results) == 1
    by_stage = await repo.get_by_stage(DealStage.lead)
    assert len(by_stage) == 1


@pytest.mark.asyncio
async def test_base_repository_count_and_update(session):
    rep = await _make_user(session, email="br@test.com")
    repo = ClientRepository(session)
    await repo.create(
        {"company_name": "A", "assigned_to": rep.id, "status": ClientStatus.active}
    )
    await session.flush()
    count = await repo.count()
    assert count == 1
    # update on missing — returns None
    result = await repo.update(99999, {"company_name": "X"})
    assert result is None
