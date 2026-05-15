"""Seed the database with demo data.

Usage:
    python -m scripts.seed_db
"""
import asyncio
from decimal import Decimal

from app.core.database import async_session_maker, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.client import Client, ClientStatus
from app.models.deal import Deal, DealStage
from app.models.user import User, UserRole


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("Admin123!"),
            full_name="Admin Demo",
            role=UserRole.admin,
        )
        manager = User(
            email="manager@example.com",
            hashed_password=hash_password("Manager123!"),
            full_name="Manager Demo",
            role=UserRole.manager,
        )
        rep = User(
            email="rep@example.com",
            hashed_password=hash_password("Rep123!"),
            full_name="Rep Demo",
            role=UserRole.sales_rep,
        )
        session.add_all([admin, manager, rep])
        await session.flush()

        client = Client(
            company_name="Acme Corporation",
            contact_person="Ivan Petrov",
            email="info@acme.example",
            source="website",
            status=ClientStatus.active,
            assigned_to=rep.id,
        )
        session.add(client)
        await session.flush()

        session.add_all(
            [
                Deal(
                    title="Pilot project",
                    amount=Decimal("250000.00"),
                    stage=DealStage.qualified,
                    client_id=client.id,
                    assigned_to=rep.id,
                ),
                Deal(
                    title="Enterprise contract",
                    amount=Decimal("1500000.00"),
                    stage=DealStage.proposal,
                    client_id=client.id,
                    assigned_to=rep.id,
                ),
            ]
        )
        await session.commit()
        print("Seed data inserted.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
