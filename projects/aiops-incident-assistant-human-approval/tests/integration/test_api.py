import asyncio
import httpx
from aiops_incident_assistant_human_approval.api.app import app

class ASGIClient:
    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
                return await session.request(method, path, **kwargs)
        return asyncio.run(send())
    def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self.request("POST", path, **kwargs)

client = ASGIClient()

def test_full_incident_flow():
    # 1. Health
    assert client.get("/health").status_code == 200
    
    # 2. Generate Incidents (Acceptance Criteria 1)
    scenarios = [
        ("latency_spike", "api-service"),
        ("high_error_rate", "auth-service"),
        ("queue_backlog", "worker-service")
    ]
    
    incident_ids = []
    for inc_type, service in scenarios:
        resp = client.post("/api/incidents/generate", json={"type": inc_type, "service_name": service})
        assert resp.status_code == 200
        incident_ids.append(resp.json()["id"])
        
    # We will trace the lifecycle of the queue_backlog incident (which has a blocked action)
    queue_incident_id = incident_ids[2]
    
    # 3. Analyze Incident (Acceptance Criteria 2 & 4)
    resp_plan = client.post(f"/api/incidents/{queue_incident_id}/analyze")
    assert resp_plan.status_code == 200
    plan = resp_plan.json()
    assert len(plan["actions"]) == 2
    
    # The second action should be BLOCKED because it's "rm -rf"
    assert plan["actions"][0]["status"] == "pending"
    assert plan["actions"][1]["status"] == "blocked"
    
    plan_id = plan["id"]
    
    # 4. Approve Action (Acceptance Criteria 3)
    # Approving blocked action should fail
    resp_fail = client.post(f"/api/plans/{plan_id}/approve", json={"action_index": 1})
    assert resp_fail.status_code == 409
    
    # Approving valid action should succeed
    resp_approve = client.post(f"/api/plans/{plan_id}/approve", json={
        "action_index": 0,
        "actor": "on-call-sre",
        "reason": "Runbook and telemetry support a safe worker restart"
    })
    assert resp_approve.status_code == 200
    assert resp_approve.json()["actions"][0]["status"] == "completed"
    assert "Local safe executor" in resp_approve.json()["actions"][0]["execution_output"]
    
    # After approving the only valid action, the incident should resolve and generate a report
    # 5. Check Reports (Acceptance Criteria 5)
    resp_reports = client.get("/api/reports")
    assert resp_reports.status_code == 200
    reports = resp_reports.json()
    assert len(reports) == 1
    assert reports[0]["incident_id"] == queue_incident_id
    assert reports[0]["root_cause"] == plan["hypothesis"]

    # Evidence, decisions, execution, and resolution remain traceable.
    audit = client.get("/api/audit", params={"incident_id": queue_incident_id}).json()
    assert {item["event_type"] for item in audit} >= {
        "incident.created", "plan.created", "action.approved", "action.completed", "incident.resolved"
    }
    export = client.get(f"/api/reports/{reports[0]['id']}/export")
    assert export.status_code == 200
    assert "## Evidence" in export.text

def test_reject_and_duplicate_decision_are_safe():
    incident = client.post("/api/incidents/generate", json={"type": "latency_spike", "service_name": "catalog-api"}).json()
    plan = client.post(f"/api/incidents/{incident['id']}/analyze").json()
    payload = {"action_index": 0, "actor": "incident-commander", "reason": "Capacity is already recovering"}
    rejected = client.post(f"/api/plans/{plan['id']}/reject", json=payload)
    assert rejected.status_code == 200
    assert rejected.json()["actions"][0]["status"] == "rejected"
    assert client.post(f"/api/plans/{plan['id']}/reject", json=payload).status_code == 409



def test_latest_plan_and_report_can_be_reopened_per_incident():
    from uuid import uuid4
    incident = client.post("/api/incidents/generate", json={"type": "queue_backlog", "service_name": "reopen-worker"}).json()
    assert client.get(f"/api/incidents/{incident['id']}/plans").json() == []
    first = client.post(f"/api/incidents/{incident['id']}/analyze").json()
    second = client.post(f"/api/incidents/{incident['id']}/analyze").json()
    plans = client.get(f"/api/incidents/{incident['id']}/plans").json()
    assert [plan["id"] for plan in plans] == [first["id"], second["id"]]
    assert [plan["revision"] for plan in plans] == [1, 2]
    assert client.get(f"/api/incidents/{uuid4()}/plans").status_code == 404

    assert client.get("/api/reports", params={"incident_id": incident["id"]}).json() == []
    client.post(f"/api/plans/{second['id']}/approve", json={"action_index": 0})
    reports = client.get("/api/reports", params={"incident_id": incident["id"]}).json()
    assert len(reports) == 1 and reports[0]["incident_id"] == incident["id"]


def test_out_of_range_action_index_is_a_client_error():
    incident = client.post("/api/incidents/generate", json={"type": "latency_spike", "service_name": "index-api"}).json()
    plan = client.post(f"/api/incidents/{incident['id']}/analyze").json()
    response = client.post(f"/api/plans/{plan['id']}/approve", json={"action_index": 5})
    assert response.status_code == 422
