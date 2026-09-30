from uuid import uuid4
from datetime import datetime, timezone
import asyncio
import httpx

from real_time_fraud_risk_stream_analytics.api.app import app

class ASGIClient:
    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
                return await session.request(method, path, **kwargs)
        return asyncio.run(send())
    def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self.request("POST", path, **kwargs)

client = ASGIClient()


def test_full_stream_and_analyst_flow():
    assert client.get("/health").status_code == 200

    seeded = client.post("/api/demo/seed")
    assert seeded.status_code == 200
    outcomes = seeded.json()
    assert len(outcomes) == 17
    assert all(item["status"] == "accepted" for item in outcomes)
    alerts = [item["alert"] for item in outcomes if item["alert"] is not None]
    assert [item["event"]["user_id"] for item in alerts] == ["synthetic-user-100", "synthetic-user-200", "synthetic-user-300"]
    assert all(item["score"]["total_risk_score"] >= 0.5 for item in alerts)
    alert = alerts[0]
    assert {"AMOUNT_ANOMALY", "GEO_ANOMALY", "DEVICE_CHANGE", "HIGH_ANOMALY_SCORE"} <= set(alert["score"]["reason_codes"])
    assert "FAILED_ATTEMPTS" in alerts[1]["score"]["reason_codes"]
    assert alert["score"]["model_version"] == "statistical-v1"

    queue = client.get("/api/alerts", params={"status": "pending"})
    assert queue.status_code == 200
    # The queue is prioritized by risk, highest first.
    assert [item["id"] for item in queue.json()] == [item["id"] for item in sorted(alerts, key=lambda item: -item["score"]["total_risk_score"])]
    assert queue.json()[0]["id"] == alert["id"]

    timeline = client.get(f"/api/entities/{alert['event']['user_id']}/timeline")
    assert timeline.status_code == 200
    assert len(timeline.json()) == 7

    feedback = client.post(f"/api/alerts/{alert['id']}/feedback", json={
        "feedback": "true_positive",
        "actor": "analyst-07",
        "note": "New device, country change, and amount spike confirmed",
        "expected_version": 1,
    })
    assert feedback.status_code == 200
    assert feedback.json()["status"] == "true_positive"
    assert feedback.json()["version"] == 2
    assert client.post(f"/api/alerts/{alert['id']}/feedback", json={
        "feedback": "false_positive", "actor": "analyst-08", "note": "conflicting review", "expected_version": 1
    }).status_code == 409

    metrics = client.get("/api/metrics").json()
    assert metrics["total_events"] == 17
    assert metrics["total_alerts"] == 3
    assert metrics["pending_alerts"] == 2
    assert metrics["true_positives"] == 1
    assert metrics["precision"] == 1.0
    assert metrics["drift_index"] is not None
    exported = client.get("/api/feedback/export")
    assert exported.status_code == 200
    assert "analyst-07" in exported.text


def test_normal_and_duplicate_event_outcomes():
    event_id = str(uuid4())
    payload = {
        "id": event_id,
        "user_id": "synthetic-normal-200",
        "type": "transaction",
        "amount": 25,
        "location": "US",
        "device_id": "known-device",
    }
    first = client.post("/api/events", json=payload)
    assert first.status_code == 200
    assert first.json()["status"] == "accepted"
    assert first.json()["alert"] is None
    duplicate = client.post("/api/events", json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate"


def test_browser_timestamp_after_seed_and_default_timestamp_can_mix():
    assert client.post("/api/demo/seed").status_code == 200
    payload = {
        "user_id": "synthetic-user-100", "type": "transaction", "amount": 20,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    browser_event = client.post("/api/events", json=payload)
    assert browser_event.status_code == 200
    assert browser_event.json()["status"] == "accepted"
    payload.pop("timestamp")
    assert client.post("/api/events", json=payload).status_code == 200
    timeline = client.get("/api/entities/synthetic-user-100/timeline")
    assert timeline.status_code == 200
    assert len(timeline.json()) == 9


def test_seed_is_repeatable_and_resets_state():
    first = client.post("/api/demo/seed").json()
    second = client.post("/api/demo/seed").json()
    scores = lambda outcomes: [item["score"]["total_risk_score"] for item in outcomes]
    assert scores(first) == scores(second)
    assert client.get("/api/metrics").json()["total_events"] == len(second)


def test_feedback_rejects_pending_and_unknown_alerts():
    client.post("/api/demo/seed")
    alert = client.get("/api/alerts").json()[0]
    pending = client.post(f"/api/alerts/{alert['id']}/feedback", json={
        "feedback": "pending", "actor": "analyst-07", "note": "not a decision", "expected_version": 1,
    })
    assert pending.status_code == 422
    missing = client.post(f"/api/alerts/{uuid4()}/feedback", json={
        "feedback": "true_positive", "actor": "analyst-07", "note": "unknown alert", "expected_version": 1,
    })
    assert missing.status_code == 404


def test_needs_more_information_is_not_final():
    client.post("/api/demo/seed")
    alert = client.get("/api/alerts").json()[0]
    body = {"actor": "analyst-07", "note": "Need customer contact"}
    held = client.post(f"/api/alerts/{alert['id']}/feedback", json={**body, "feedback": "needs_more_information", "expected_version": 1})
    assert held.status_code == 200 and held.json()["version"] == 2
    final = client.post(f"/api/alerts/{alert['id']}/feedback", json={**body, "feedback": "false_positive", "expected_version": 2})
    assert final.status_code == 200
    metrics = client.get("/api/metrics").json()
    assert metrics["reviewed_alerts"] == 1 and metrics["false_positive_rate"] == 1.0 and metrics["precision"] == 0.0
