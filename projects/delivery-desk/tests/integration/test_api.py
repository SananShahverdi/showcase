from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from delivery_desk.api.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "tasks.sqlite3")) as client:
        yield client


def test_task_lifecycle_records_changes_and_detects_stale_edits(client):
    response = client.post("/api/tasks", json={"title": "Ship search", "project": "Portal", "due_date": "2026-10-01"})
    assert response.status_code == 201
    task = response.json()
    response = client.patch(f"/api/tasks/{task['id']}", json={"version": 1, "status": "in_progress", "due_date": None})
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["due_date"] is None
    stale = client.patch(f"/api/tasks/{task['id']}", json={"version": 1, "title": "Overwritten"})
    assert stale.status_code == 409
    detail = client.get(f"/api/tasks/{task['id']}").json()
    assert detail["title"] == "Ship search"
    assert len(detail["history"]) == 2
    assert detail["history"][0]["changes"]["status"] == {"from": "backlog", "to": "in_progress"}


def test_filters_and_validation(client):
    client.post("/api/tasks", json={"title": "Invoice export", "project": "Portal", "priority": "high"})
    client.post("/api/tasks", json={"title": "Dashboard", "project": "Operations"})
    assert len(client.get("/api/tasks?q=INVOICE&project=Portal&priority=high").json()["items"]) == 1
    assert client.get("/api/tasks?q=%").json()["items"] == []
    assert client.post("/api/tasks", json={"title": "   "}).status_code == 422
    assert client.post("/api/tasks", json={"title": "Task", "status": "missing"}).status_code == 422
    assert client.patch("/api/tasks/1", json={"version": 1, "title": None}).status_code == 422
    assert client.get("/api/tasks/999").status_code == 404


def test_seed_is_idempotent_and_preserves_existing_tasks(client):
    client.post("/api/tasks", json={"title": "My existing task"})
    assert client.post("/api/demo/seed").json()["added"] == 6
    assert client.post("/api/demo/seed").json()["added"] == 0
    assert len(client.get("/api/tasks").json()["items"]) == 7


def test_storage_survives_new_app(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(path)) as first:
        first.post("/api/tasks", json={"title": "Still here"})
    with TestClient(create_app(path)) as second:
        assert second.get("/api/tasks").json()["items"][0]["title"] == "Still here"


def test_concurrent_edits_allow_only_one_winner(client):
    task = client.post("/api/tasks", json={"title": "Task"}).json()
    def edit(title):
        return client.patch(f"/api/tasks/{task['id']}", json={"version": 1, "title": title}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, ["First edit", "Second edit"])) == [200, 409]
