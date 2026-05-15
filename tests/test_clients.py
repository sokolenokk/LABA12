import pytest


@pytest.mark.asyncio
async def test_create_client(client, sales_rep_headers):
    resp = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Acme", "email": "a@acme.com"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["company_name"] == "Acme"
    assert data["assigned_to"] is not None


@pytest.mark.asyncio
async def test_create_client_invalid(client, sales_rep_headers):
    resp = await client.post(
        "/api/v1/clients/",
        json={"company_name": "", "email": "bad-email"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sales_rep_sees_only_own_clients(
    client, sales_rep_headers, other_rep_headers
):
    await client.post(
        "/api/v1/clients/",
        json={"company_name": "Own"},
        headers=sales_rep_headers,
    )
    await client.post(
        "/api/v1/clients/",
        json={"company_name": "Other"},
        headers=other_rep_headers,
    )
    resp = await client.get("/api/v1/clients/", headers=sales_rep_headers)
    assert resp.status_code == 200
    names = {c["company_name"] for c in resp.json()}
    assert names == {"Own"}


@pytest.mark.asyncio
async def test_manager_sees_all_clients(client, sales_rep_headers, manager_headers):
    await client.post(
        "/api/v1/clients/",
        json={"company_name": "Acme"},
        headers=sales_rep_headers,
    )
    await client.post(
        "/api/v1/clients/",
        json={"company_name": "Globex"},
        headers=manager_headers,
    )
    resp = await client.get("/api/v1/clients/", headers=manager_headers)
    assert resp.status_code == 200
    names = {c["company_name"] for c in resp.json()}
    assert {"Acme", "Globex"}.issubset(names)


@pytest.mark.asyncio
async def test_get_own_client(client, sales_rep_headers):
    created = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Acme"},
        headers=sales_rep_headers,
    )
    cid = created.json()["id"]
    resp = await client.get(f"/api/v1/clients/{cid}", headers=sales_rep_headers)
    assert resp.status_code == 200
    assert resp.json()["company_name"] == "Acme"


@pytest.mark.asyncio
async def test_get_missing_client(client, sales_rep_headers):
    resp = await client.get("/api/v1/clients/9999", headers=sales_rep_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sales_rep_cannot_get_others_client(
    client, sales_rep_headers, other_rep_headers
):
    created = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Foreign"},
        headers=other_rep_headers,
    )
    cid = created.json()["id"]
    resp = await client.get(f"/api/v1/clients/{cid}", headers=sales_rep_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_own_client(client, sales_rep_headers):
    created = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Old"},
        headers=sales_rep_headers,
    )
    cid = created.json()["id"]
    resp = await client.put(
        f"/api/v1/clients/{cid}",
        json={"company_name": "New"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["company_name"] == "New"


@pytest.mark.asyncio
async def test_sales_rep_cannot_update_others_client(
    client, sales_rep_headers, other_rep_headers
):
    created = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Foreign"},
        headers=other_rep_headers,
    )
    cid = created.json()["id"]
    resp = await client.put(
        f"/api/v1/clients/{cid}",
        json={"company_name": "Hijacked"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_delete_client(client, admin_headers, sales_rep_headers):
    created = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Doomed"},
        headers=sales_rep_headers,
    )
    cid = created.json()["id"]
    resp = await client.delete(f"/api/v1/clients/{cid}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_sales_rep_cannot_delete_client(client, sales_rep_headers):
    created = await client.post(
        "/api/v1/clients/",
        json={"company_name": "Mine"},
        headers=sales_rep_headers,
    )
    cid = created.json()["id"]
    resp = await client.delete(f"/api/v1/clients/{cid}", headers=sales_rep_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_search_clients(client, sales_rep_headers):
    await client.post(
        "/api/v1/clients/",
        json={"company_name": "Acme Corp"},
        headers=sales_rep_headers,
    )
    await client.post(
        "/api/v1/clients/",
        json={"company_name": "Globex"},
        headers=sales_rep_headers,
    )
    resp = await client.get(
        "/api/v1/clients/search?q=acme", headers=sales_rep_headers
    )
    assert resp.status_code == 200
    names = {c["company_name"] for c in resp.json()}
    assert "Acme Corp" in names
    assert "Globex" not in names


@pytest.mark.asyncio
async def test_delete_missing_client(client, admin_headers):
    resp = await client.delete("/api/v1/clients/9999", headers=admin_headers)
    assert resp.status_code == 404
