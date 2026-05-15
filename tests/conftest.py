import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.base import Base

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_maker(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_maker):
    async with session_maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(async_engine, session_maker):
    async def override_get_db():
        async with session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    # disable startup lifespan because schema is already created by async_engine fixture
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def register_and_login(
    client: AsyncClient,
    email: str,
    password: str = "Strong123!",
    role: str = "sales_rep",
    full_name: str = "Test User",
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client):
    return await register_and_login(client, "admin@test.com", role="admin", full_name="Admin")


@pytest_asyncio.fixture
async def manager_headers(client):
    return await register_and_login(client, "manager@test.com", role="manager", full_name="Manager")


@pytest_asyncio.fixture
async def sales_rep_headers(client):
    return await register_and_login(client, "rep@test.com", role="sales_rep", full_name="Sales Rep")


@pytest_asyncio.fixture
async def other_rep_headers(client):
    return await register_and_login(client, "rep2@test.com", role="sales_rep", full_name="Other Rep")
