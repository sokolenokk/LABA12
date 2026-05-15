import pytest


async def _make_client(client, headers):
    resp = await client.post(
        "/api/v1/clients/", json={"company_name": "Acme"}, headers=headers
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_contact(client, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    resp = await client.post(
        "/api/v1/contacts/",
        json={
            "first_name": "Ivan",
            "last_name": "Petrov",
            "email": "ivan@acme.com",
            "client_id": cid,
            "is_primary": True,
        },
        headers=sales_rep_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["first_name"] == "Ivan"


@pytest.mark.asyncio
async def test_create_contact_unknown_client(client, sales_rep_headers):
    resp = await client.post(
        "/api/v1/contacts/",
        json={
            "first_name": "Ghost",
            "last_name": "Phantom",
            "client_id": 99999,
        },
        headers=sales_rep_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_contacts_by_client(client, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    await client.post(
        "/api/v1/contacts/",
        json={"first_name": "A", "last_name": "A", "client_id": cid},
        headers=sales_rep_headers,
    )
    resp = await client.get(
        f"/api/v1/contacts/?client_id={cid}", headers=sales_rep_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_sales_rep_cannot_add_contact_to_others_client(
    client, sales_rep_headers, other_rep_headers
):
    cid = await _make_client(client, other_rep_headers)
    resp = await client.post(
        "/api/v1/contacts/",
        json={"first_name": "X", "last_name": "X", "client_id": cid},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_contact(client, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    created = await client.post(
        "/api/v1/contacts/",
        json={"first_name": "Old", "last_name": "Name", "client_id": cid},
        headers=sales_rep_headers,
    )
    contact_id = created.json()["id"]
    resp = await client.put(
        f"/api/v1/contacts/{contact_id}",
        json={"first_name": "New"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "New"


@pytest.mark.asyncio
async def test_admin_can_delete_contact(client, admin_headers, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    created = await client.post(
        "/api/v1/contacts/",
        json={"first_name": "Bye", "last_name": "Bye", "client_id": cid},
        headers=sales_rep_headers,
    )
    contact_id = created.json()["id"]
    resp = await client.delete(f"/api/v1/contacts/{contact_id}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_sales_rep_cannot_delete_contact(client, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    created = await client.post(
        "/api/v1/contacts/",
        json={"first_name": "X", "last_name": "X", "client_id": cid},
        headers=sales_rep_headers,
    )
    contact_id = created.json()["id"]
    resp = await client.delete(
        f"/api/v1/contacts/{contact_id}", headers=sales_rep_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_missing_contact(client, sales_rep_headers):
    resp = await client.put(
        "/api/v1/contacts/9999",
        json={"first_name": "Ghost"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 404
