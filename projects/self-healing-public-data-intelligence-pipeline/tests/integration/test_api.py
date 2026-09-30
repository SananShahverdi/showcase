from fastapi.testclient import TestClient

from self_healing_public_data_intelligence_pipeline.api.app import app
from self_healing_public_data_intelligence_pipeline.api.routes import repo

client = TestClient(app)


def test_extract_quarantine_replay_and_activate():
    repo.reset()
    source = client.post("/api/sources", json={
        "url": "fixture://catalog", "name": "Catalog",
        "selectors": {"_record": "article", "title": "h2", "price": ".old-price"},
        "expected_schema": {"title": "str", "price": "float"},
    })
    assert source.status_code == 200
    source_id = source.json()["id"]
    html = "<article><h2>Apples</h2><span data-field='price'>2.50</span></article>"
    run = client.post("/api/crawl", json={"source_id": source_id, "html_content": html})
    assert run.status_code == 200
    assert run.json()["quarantined_count"] == 1
    assert client.get("/api/records/valid").json() == []

    failures = client.get("/api/failures").json()
    assert failures[0]["field"] == "price"
    proposal = client.post(f"/api/repair/propose/{failures[0]['id']}")
    assert proposal.status_code == 200
    proposal_id = proposal.json()["id"]
    assert proposal.json()["proposed_selectors"]["price"] == "[data-field='price']"
    assert client.post(f"/api/repair/activate/{proposal_id}", json={"approved": True}).status_code == 409

    replay = client.post(f"/api/repair/replay/{proposal_id}", json={"test_html": html})
    assert replay.status_code == 200
    assert replay.json()["replay_passed"] is True
    activated = client.post(f"/api/repair/activate/{proposal_id}", json={"approved": True})
    assert activated.status_code == 200
    assert activated.json()["version"] == 2
    second = client.post("/api/crawl", json={"source_id": source_id, "html_content": html})
    assert second.json()["valid_count"] == 1
    assert len(client.get("/api/records/valid").json()) == 1


def test_demo_seed_resets_and_dashboard_reports_the_quality_gate():
    for _ in range(2):  # reloading the fixture fleet replaces it rather than duplicating it
        assert client.post("/api/demo/seed").status_code == 200
    assert len(client.get("/api/sources").json()) == 1
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["extraction_trends"] == {
        "total_extracted": 2, "valid_records": 1, "quarantined_records": 1, "success_rate": 0.5, "drifted_runs": 0,
    }
    assert dashboard["source_health"]["degraded"] == 1
    runs = client.get("/api/runs").json()
    assert [(run["extracted_count"], run["valid_count"]) for run in runs] == [(2, 1)]
    recipes = client.get("/api/recipes").json()
    assert [(recipe["version"], recipe["is_active"], recipe["success_rate"]) for recipe in recipes] == [(1, True, 0.5)]

