import pytest


async def _make_client_for(client, headers):
    resp = await client.post(
        "/api/v1/clients/", json={"company_name": "Acme"}, headers=headers
    )
    return resp.json()["id"]


async def _make_deal(client, headers, amount="1000.00", stage="lead"):
    cid = await _make_client_for(client, headers)
    resp = await client.post(
        "/api/v1/deals/",
        json={
            "title": "Deal",
            "amount": amount,
            "client_id": cid,
            "stage": stage,
        },
        headers=headers,
    )
    return resp.json()


async def _drive_to(client, headers, deal_id, target):
    chain = {
        "qualified": ["qualified"],
        "proposal": ["qualified", "proposal"],
        "negotiation": ["qualified", "proposal", "negotiation"],
        "won": ["qualified", "proposal", "negotiation", "won"],
        "lost": ["lost"],
    }
    for stage in chain[target]:
        r = await client.patch(
            f"/api/v1/deals/{deal_id}/stage",
            json={"stage": stage},
            headers=headers,
        )
        assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_funnel_structure(client, manager_headers):
    resp = await client.get("/api/v1/analytics/funnel", headers=manager_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "stages" in body
    stage_names = {s["stage"] for s in body["stages"]}
    assert {
        "lead",
        "qualified",
        "proposal",
        "negotiation",
        "won",
        "lost",
    } == stage_names
    assert "total_deals" in body
    assert "total_amount" in body


@pytest.mark.asyncio
async def test_funnel_counts_deals(client, manager_headers, sales_rep_headers):
    await _make_deal(client, sales_rep_headers, amount="100.00")
    await _make_deal(client, sales_rep_headers, amount="200.00")
    resp = await client.get("/api/v1/analytics/funnel", headers=manager_headers)
    body = resp.json()
    assert body["total_deals"] == 2
    lead_stage = next(s for s in body["stages"] if s["stage"] == "lead")
    assert lead_stage["count"] == 2


@pytest.mark.asyncio
async def test_kpi_zero_win_rate(client, manager_headers, sales_rep_headers):
    await _make_deal(client, sales_rep_headers)
    resp = await client.get("/api/v1/analytics/kpi", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["win_rate"] == 0.0


@pytest.mark.asyncio
async def test_kpi_positive_win_rate(client, manager_headers, sales_rep_headers):
    won = await _make_deal(client, sales_rep_headers, amount="500.00")
    lost = await _make_deal(client, sales_rep_headers, amount="100.00")
    await _drive_to(client, sales_rep_headers, won["id"], "won")
    await _drive_to(client, sales_rep_headers, lost["id"], "lost")
    resp = await client.get("/api/v1/analytics/kpi", headers=manager_headers)
    body = resp.json()
    assert body["win_rate"] == 0.5
    assert float(body["total_won_amount"]) == 500.0
    assert float(body["total_lost_amount"]) == 100.0


@pytest.mark.asyncio
async def test_manager_stats_admin_only(
    client, admin_headers, manager_headers, sales_rep_headers
):
    deal = await _make_deal(client, sales_rep_headers, amount="1000.00")
    await _drive_to(client, sales_rep_headers, deal["id"], "won")

    forbidden = await client.get(
        "/api/v1/analytics/manager-stats", headers=sales_rep_headers
    )
    assert forbidden.status_code == 403

    forbidden_mgr = await client.get(
        "/api/v1/analytics/manager-stats", headers=manager_headers
    )
    assert forbidden_mgr.status_code == 403

    ok = await client.get("/api/v1/analytics/manager-stats", headers=admin_headers)
    assert ok.status_code == 200
    managers = ok.json()["managers"]
    assert any(m["deals_won"] >= 1 for m in managers)


@pytest.mark.asyncio
async def test_sales_rep_cannot_access_analytics(client, sales_rep_headers):
    resp = await client.get("/api/v1/analytics/funnel", headers=sales_rep_headers)
    assert resp.status_code == 403
