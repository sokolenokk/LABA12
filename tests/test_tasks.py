from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_create_task(client, sales_rep_headers):
    resp = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Call client",
            "priority": "high",
            "task_type": "call",
        },
        headers=sales_rep_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Call client"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_list_tasks_sales_rep_sees_own(
    client, sales_rep_headers, other_rep_headers
):
    await client.post(
        "/api/v1/tasks/",
        json={"title": "Mine"},
        headers=sales_rep_headers,
    )
    await client.post(
        "/api/v1/tasks/",
        json={"title": "Theirs"},
        headers=other_rep_headers,
    )
    resp = await client.get("/api/v1/tasks/", headers=sales_rep_headers)
    titles = {t["title"] for t in resp.json()}
    assert titles == {"Mine"}


@pytest.mark.asyncio
async def test_list_overdue_returns_only_overdue(client, sales_rep_headers):
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    await client.post(
        "/api/v1/tasks/",
        json={"title": "Late", "due_date": past},
        headers=sales_rep_headers,
    )
    await client.post(
        "/api/v1/tasks/",
        json={"title": "Soon", "due_date": future},
        headers=sales_rep_headers,
    )
    resp = await client.get("/api/v1/tasks/overdue", headers=sales_rep_headers)
    titles = [t["title"] for t in resp.json()]
    assert titles == ["Late"]


@pytest.mark.asyncio
async def test_change_status(client, sales_rep_headers):
    created = await client.post(
        "/api/v1/tasks/",
        json={"title": "T"},
        headers=sales_rep_headers,
    )
    tid = created.json()["id"]
    resp = await client.patch(
        f"/api/v1/tasks/{tid}/status",
        json={"status": "completed"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_update_task(client, sales_rep_headers):
    created = await client.post(
        "/api/v1/tasks/",
        json={"title": "Old", "priority": "low"},
        headers=sales_rep_headers,
    )
    tid = created.json()["id"]
    resp = await client.put(
        f"/api/v1/tasks/{tid}",
        json={"title": "New", "priority": "urgent"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New"
    assert body["priority"] == "urgent"


@pytest.mark.asyncio
async def test_sales_rep_cannot_access_others_task(
    client, sales_rep_headers, other_rep_headers
):
    created = await client.post(
        "/api/v1/tasks/",
        json={"title": "Foreign"},
        headers=other_rep_headers,
    )
    tid = created.json()["id"]
    resp = await client.put(
        f"/api/v1/tasks/{tid}",
        json={"title": "Hijacked"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_delete_task(client, admin_headers, sales_rep_headers):
    created = await client.post(
        "/api/v1/tasks/",
        json={"title": "Bye"},
        headers=sales_rep_headers,
    )
    tid = created.json()["id"]
    resp = await client.delete(f"/api/v1/tasks/{tid}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_sales_rep_cannot_delete_task(client, sales_rep_headers):
    created = await client.post(
        "/api/v1/tasks/",
        json={"title": "Mine"},
        headers=sales_rep_headers,
    )
    tid = created.json()["id"]
    resp = await client.delete(f"/api/v1/tasks/{tid}", headers=sales_rep_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_missing_task_404(client, sales_rep_headers):
    resp = await client.put(
        "/api/v1/tasks/9999",
        json={"title": "Ghost"},
        headers=sales_rep_headers,
    )
    assert resp.status_code == 404
