import pytest


@pytest.mark.asyncio
async def test_admin_lists_users(client, admin_headers, sales_rep_headers):
    # both fixtures register users
    resp = await client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert "admin@test.com" in emails
    assert "rep@test.com" in emails


@pytest.mark.asyncio
async def test_manager_lists_users(client, manager_headers, sales_rep_headers):
    resp = await client.get("/api/v1/users/", headers=manager_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sales_rep_cannot_list_users(client, sales_rep_headers):
    resp = await client.get("/api/v1/users/", headers=sales_rep_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_id(client, admin_headers, sales_rep_headers):
    listing = await client.get("/api/v1/users/", headers=admin_headers)
    target = next(u for u in listing.json() if u["email"] == "rep@test.com")
    resp = await client.get(f"/api/v1/users/{target['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "rep@test.com"


@pytest.mark.asyncio
async def test_get_missing_user(client, admin_headers):
    resp = await client.get("/api/v1/users/9999", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_only_admin_can_deactivate(client, manager_headers, sales_rep_headers):
    # manager cannot deactivate
    listing = await client.get("/api/v1/users/", headers=manager_headers)
    target = next(u for u in listing.json() if u["email"] == "rep@test.com")
    resp = await client.patch(
        f"/api/v1/users/{target['id']}/deactivate", headers=manager_headers
    )
    assert resp.status_code == 403
