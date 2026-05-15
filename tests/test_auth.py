import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@test.com",
            "password": "Strong123!",
            "full_name": "New User",
            "role": "sales_rep",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "sales_rep"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "dup@test.com",
        "password": "Strong123!",
        "full_name": "User",
        "role": "sales_rep",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "Strong123!",
            "full_name": "X",
            "role": "sales_rep",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@test.com",
            "password": "short",
            "full_name": "X",
            "role": "sales_rep",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@test.com",
            "password": "Strong123!",
            "full_name": "L",
            "role": "sales_rep",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "login@test.com", "password": "Strong123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@test.com",
            "password": "Strong123!",
            "full_name": "L",
            "role": "sales_rep",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpw@test.com", "password": "Bad"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@test.com", "password": "Strong123!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client, sales_rep_headers):
    resp = await client.get("/api/v1/auth/me", headers=sales_rep_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "rep@test.com"


@pytest.mark.asyncio
async def test_me_without_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_login_blocked(client, admin_headers):
    # admin registers a sales_rep then deactivates them
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "inactive@test.com",
            "password": "Strong123!",
            "full_name": "Will Be Inactive",
            "role": "sales_rep",
        },
    )
    users = await client.get("/api/v1/users/", headers=admin_headers)
    target = next(u for u in users.json() if u["email"] == "inactive@test.com")
    deact = await client.patch(
        f"/api/v1/users/{target['id']}/deactivate", headers=admin_headers
    )
    assert deact.status_code == 200
    # now login should be rejected
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@test.com", "password": "Strong123!"},
    )
    assert resp.status_code == 401
