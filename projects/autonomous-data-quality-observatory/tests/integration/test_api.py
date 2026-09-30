import httpx
import pytest

from autonomous_data_quality_observatory.api.app import app

@pytest.fixture
def anyio_backend():
    return "asyncio"


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_seed_drift_deduplicate_and_resolve_journey():
  async with client() as api:
    await api.delete("/api/demo/reset")
    assert (await api.get("/health")).status_code == 200
    seeded = await api.post("/api/demo/seed?reset=true")
    assert seeded.status_code == 200
    assert len(seeded.json()) == 2
    assert all(item["health_status"] == "healthy" for item in seeded.json())

    preview = await api.post("/api/sources/orders_daily/preview?limit=3")
    assert preview.status_code == 200
    assert preview.json()["row_count"] == 12
    assert len(preview.json()["rows"]) == 3

    await api.post("/api/demo/drift")
    first = await api.post("/api/observe/orders_daily")
    assert first.status_code == 200
    assert first.json()["health_status"] == "critical"
    assert first.json()["drift_result"]["has_drift"] is True
    assert first.json()["issues_created"]

    second = await api.post("/api/observe/orders_daily")
    assert second.status_code == 200
    assert second.json()["issues_created"] == []
    assert second.json()["issues_updated"]
    issue = second.json()["issues_updated"][0]
    assert issue["occurrence_count"] == 2

    resolved = await api.patch(
        f"/api/issues/{issue['id']}",
        json={"status": "resolved", "actor": "qa-owner", "comment": "Upstream contract accepted."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert any(event["action"] == "commented" for event in resolved.json()["timeline"])

    exported = await api.post(f"/api/issues/{issue['id']}/export")
    assert exported.status_code == 200
    assert exported.json()["delivered"] is False
    assert exported.json()["payload"]["summary"]


@pytest.mark.anyio
async def test_real_inline_source_and_rule_validation():
  async with client() as api:
    await api.delete("/api/demo/reset")
    source = {
        "id": "payments",
        "name": "Payments",
        "type": "inline",
        "config": {"records": [{"id": 1, "amount": 25}, {"id": 2, "amount": -2}]},
        "owner": "finance-data",
    }
    assert (await api.post("/api/sources", json=source)).status_code == 201
    rule = {
        "id": "positive-amounts",
        "source_id": "payments",
        "rule_type": "business_expression",
        "parameters": {"expression": "amount >= 0", "max_failures": 0},
        "severity": "critical",
    }
    assert (await api.post("/api/rules", json=rule)).status_code == 201
    report = await api.post("/api/observe/payments")
    assert report.status_code == 200
    assert report.json()["rule_results"][0]["passed"] is False


@pytest.mark.anyio
async def test_connector_errors_are_explicit_and_not_fabricated():
  async with client() as api:
    await api.delete("/api/demo/reset")
    source = {"id": "warehouse", "name": "Warehouse", "type": "postgres", "config": {"dsn": "secret"}}
    response = await api.post("/api/sources", json=source)
    assert response.status_code == 201
    assert response.json()["config"]["dsn"] == "***"
    observation = await api.post("/api/observe/warehouse")
    assert observation.status_code == 400
    assert "no data was fabricated" in observation.json()["detail"]
