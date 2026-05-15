from decimal import Decimal

import pytest


async def _make_client(client, headers):
    resp = await client.post(
        "/api/v1/clients/", json={"company_name": "Acme"}, headers=headers
    )
    return resp.json()["id"]


async def _make_deal(client, headers, **overrides):
    cid = await _make_client(client, headers)
    payload = {
        "title": "Deal 1",
        "amount": "1000.00",
        "currency": "RUB",
        "client_id": cid,
        "probability": 10,
        "stage": "lead",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/deals/", json=payload, headers=headers)
    return resp.json()


@pytest.mark.asyncio
async def test_create_deal(client, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    resp = await client.post(
        "/api/v1/deals/",
        json={
            "title": "Big deal",
            "amount": "150000.50",
            "currency": "RUB",
            "client_id": cid,
            "probability": 50,
        },
        headers=sales_rep_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Big deal"
    assert Decimal(body["amount"]) == Decimal("150000.50")
    assert body["stage"] == "lead"


@pytest.mark.asyncio
async def test_decimal_precision_preserved(client, sales_rep_headers):
    cid = await _make_client(client, sales_rep_headers)
    resp = await client.post(
        "/api/v1/deals/",
        json={
            "title": "Precise",
            "amount": "0.10",
            "client_id": cid,
        },
        headers=sales_rep_headers,
    )
    assert resp.status_code == 201
    deal_id = resp.json()["id"]
    fetched = await client.get(f"/api/v1/deals/{deal_id}", headers=sales_rep_headers)
    # 0.10 + 0.20 == 0.30 only with Decimal, not float
    assert Decimal(fetched.json()["amount"]) == Decimal("0.10")


@pytest.mark.asyncio
async def test_create_deal_missing_client(client, sales_rep_headers):
    resp = await client.post(
        "/api/v1/deals/",
        json={"title": "Ghost", "amount": "100.00", "client_id": 99999},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_transition_lead_to_qualified(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    resp = await client.patch(
        f"/api/v1/deals/{deal['id']}/stage",
        json={"stage": "qualified"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["stage"] == "qualified"


@pytest.mark.asyncio
async def test_transition_lead_to_won_forbidden(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    resp = await client.patch(
        f"/api/v1/deals/{deal['id']}/stage",
        json={"stage": "won"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_full_funnel_to_won(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    for stage in ["qualified", "proposal", "negotiation", "won"]:
        resp = await client.patch(
            f"/api/v1/deals/{deal['id']}/stage",
            json={"stage": stage},
            headers=sales_rep_headers,
        )
        assert resp.status_code == 200, f"failed at {stage}: {resp.text}"
        assert resp.json()["stage"] == stage


@pytest.mark.asyncio
async def test_transition_qualified_to_lost(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    await client.patch(
        f"/api/v1/deals/{deal['id']}/stage",
        json={"stage": "qualified"},
        headers=sales_rep_headers,
    )
    resp = await client.patch(
        f"/api/v1/deals/{deal['id']}/stage",
        json={"stage": "lost"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["stage"] == "lost"


@pytest.mark.asyncio
async def test_transition_from_terminal_state_forbidden(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    # drive to "lost"
    await client.patch(
        f"/api/v1/deals/{deal['id']}/stage",
        json={"stage": "lost"},
        headers=sales_rep_headers,
    )
    # any transition from "lost" must fail
    resp = await client.patch(
        f"/api/v1/deals/{deal['id']}/stage",
        json={"stage": "qualified"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_filter_deals_by_stage(client, sales_rep_headers):
    d1 = await _make_deal(client, sales_rep_headers)
    await _make_deal(client, sales_rep_headers)
    await client.patch(
        f"/api/v1/deals/{d1['id']}/stage",
        json={"stage": "qualified"},
        headers=sales_rep_headers,
    )
    resp = await client.get("/api/v1/deals/?stage=qualified", headers=sales_rep_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["stage"] == "qualified"


@pytest.mark.asyncio
async def test_sales_rep_sees_only_own_deals(
    client, sales_rep_headers, other_rep_headers
):
    await _make_deal(client, sales_rep_headers, title="Mine")
    await _make_deal(client, other_rep_headers, title="Theirs")
    resp = await client.get("/api/v1/deals/", headers=sales_rep_headers)
    titles = {d["title"] for d in resp.json()}
    assert titles == {"Mine"}


@pytest.mark.asyncio
async def test_update_deal(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    resp = await client.put(
        f"/api/v1/deals/{deal['id']}",
        json={"title": "Updated", "probability": 90},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated"
    assert body["probability"] == 90


@pytest.mark.asyncio
async def test_get_missing_deal(client, sales_rep_headers):
    resp = await client.get("/api/v1/deals/9999", headers=sales_rep_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sales_rep_cannot_access_others_deal(
    client, sales_rep_headers, other_rep_headers
):
    deal = await _make_deal(client, other_rep_headers)
    resp = await client.get(f"/api/v1/deals/{deal['id']}", headers=sales_rep_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_delete_deal(client, admin_headers, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    resp = await client.delete(f"/api/v1/deals/{deal['id']}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_sales_rep_cannot_delete_deal(client, sales_rep_headers):
    deal = await _make_deal(client, sales_rep_headers)
    resp = await client.delete(f"/api/v1/deals/{deal['id']}", headers=sales_rep_headers)
    assert resp.status_code == 403
