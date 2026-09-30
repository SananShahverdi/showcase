import httpx
import pytest

from smart_network_capacity_planner.api.app import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_seed_forecast_scenario_and_report_journey():
  async with client() as api:
    await api.delete("/api/demo/reset")
    assert (await api.get("/health")).status_code == 200
    seeded = await api.post("/api/demo/seed?reset=true")
    assert seeded.status_code == 200
    assert seeded.json()["accepted_count"] == 90

    overview = await api.get("/api/overview")
    assert overview.status_code == 200
    assert overview.json()["link_count"] == 3
    assert overview.json()["sample_count"] == 90

    link_id = overview.json()["links"][0]["link_id"]
    response = await api.get(f"/api/forecast/{link_id}?days=30&budget_usd=100")
    assert response.status_code == 200
    forecast = response.json()
    assert len(forecast["forecast_points"]) == 30
    assert forecast["diagnostics"]["method"] == "ordinary-least-squares-linear-trend"
    assert forecast["diagnostics"]["sample_count"] == 30
    assert forecast["risk"]["reasons"]
    assert all("selection_reason" in item for item in forecast["recommendations"])

    scenario = await api.post(
        f"/api/what-if/{link_id}",
        json={
            "name": "Add capacity and shift backups",
            "traffic_growth_multiplier": 1,
            "traffic_reduction_pct": 15,
            "added_capacity_mbps": 10_000,
            "forecast_days": 30,
        },
    )
    assert scenario.status_code == 201
    assert scenario.json()["headroom_delta_pct"] > 0
    assert len((await api.get(f"/api/what-if/{link_id}")).json()) == 1

    report = await api.get("/api/reports/weekly?format=markdown")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/markdown")
    assert "Weekly Network Capacity Report" in report.text
    assert link_id in report.text


@pytest.mark.anyio
async def test_ingestion_is_idempotent_and_conflicts_are_rejected():
  async with client() as api:
    await api.delete("/api/demo/reset")
    payload = [{
        "timestamp": "2026-01-01T00:00:00Z",
        "link_id": "core-1",
        "utilization_mbps": 850,
        "capacity_mbps": 1000,
        "latency_ms": 2,
        "packet_loss_pct": 0,
    }]
    first = await api.post("/api/telemetry", json=payload)
    duplicate = await api.post("/api/telemetry", json=payload)
    assert first.json()["accepted_count"] == 1
    assert duplicate.json()["duplicate_count"] == 1

    payload[0]["utilization_mbps"] = 900
    conflict = await api.post("/api/telemetry", json=payload)
    assert conflict.status_code == 409


@pytest.mark.anyio
async def test_validation_and_empty_states_are_explicit():
  async with client() as api:
    await api.delete("/api/demo/reset")
    assert (await api.post("/api/telemetry", json=[])).status_code == 400
    assert (await api.get("/api/forecast/unknown")).status_code == 404
    invalid = await api.post(
        "/api/telemetry",
        json=[{
            "timestamp": "2026-01-01T00:00:00Z",
            "link_id": "bad link id",
            "utilization_mbps": -1,
            "capacity_mbps": 0,
            "latency_ms": -2,
            "packet_loss_pct": 120,
        }],
    )
    assert invalid.status_code == 422
