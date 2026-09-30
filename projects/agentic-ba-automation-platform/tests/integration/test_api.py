from fastapi.testclient import TestClient

from agentic_ba_automation_platform.api.app import app
from agentic_ba_automation_platform.api.routes import repo, service

client = TestClient(app)


def test_ingest_review_export_audit_workflow():
    repo.reset()
    files = {"file": ("notes.md", b"Customers need a login page. Login requires email and password.", "text/markdown")}
    uploaded = client.post("/api/upload", files=files, data={"user_id": "analyst"})
    assert uploaded.status_code == 200
    assert uploaded.json()["content_hash"]

    generated = client.post("/api/generate", json={"query": "login email", "artifact_type": "acceptance_criteria", "user_id": "analyst"})
    assert generated.status_code == 200
    artifact = generated.json()
    assert "login" in artifact["content"].lower()
    assert artifact["citations"]

    artifact_id = artifact["id"]
    rejected = client.put(f"/api/artifacts/{artifact_id}/status", json={"status": "rejected", "user_id": "reviewer", "comment": "Add measurable detail"})
    assert rejected.status_code == 200
    edited = client.patch(f"/api/artifacts/{artifact_id}", json={"content": artifact["content"] + "\n4. Then an audit event is recorded.", "user_id": "analyst"})
    assert edited.json()["revision"] == 2
    approved = client.put(f"/api/artifacts/{artifact_id}/status", json={"status": "approved", "user_id": "reviewer"})
    assert approved.status_code == 200

    exported = client.post(f"/api/artifacts/{artifact_id}/export", json={"target": "jira", "user_id": "reviewer"})
    assert exported.status_code == 200
    assert exported.json()["mode"] == "local"
    assert exported.json()["payload"]["fields"]["issuetype"]["name"] == "Task"
    assert client.patch(f"/api/artifacts/{artifact_id}", json={"content": "changed", "user_id": "analyst"}).status_code == 409
    actions = {entry["action"] for entry in client.get("/api/audit").json()}
    assert {"document_ingested", "artifact_generated", "artifact_edited", "artifact_reviewed", "artifact_exported"} <= actions


def test_upload_and_generation_boundaries():
    repo.reset()
    unsupported = client.post("/api/upload", files={"file": ("data.csv", b"a,b", "text/csv")}, data={"user_id": "analyst"})
    assert unsupported.status_code == 415
    no_evidence = client.post("/api/generate", json={"query": "unknown evidence", "artifact_type": "risk", "user_id": "analyst"})
    assert no_evidence.status_code == 422


def test_github_export_is_local_even_when_credentials_are_inherited(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "synthetic/repository")
    monkeypatch.delenv("AGENTIC_BA_ALLOW_REMOTE_EXPORT", raising=False)

    def unexpected_publish(*args):
        raise AssertionError("Local preview must not contact GitHub")

    monkeypatch.setattr(service, "_create_github_issue", unexpected_publish)
    service.seed_demo()
    artifact = repo.get_artifacts()[0]
    approved = client.put(f"/api/artifacts/{artifact.id}/status", json={"status": "approved", "user_id": "reviewer"})
    assert approved.status_code == 200
    exported = client.post(f"/api/artifacts/{artifact.id}/export", json={"target": "github", "user_id": "reviewer"})
    assert exported.status_code == 200
    assert exported.json()["mode"] == "preview"
    assert exported.json()["remote_url"] is None
    assert exported.json()["payload"]["title"]
    assert repo.get_artifact(artifact.id).status.value == "approved"


def test_upload_falls_back_to_extension_when_browser_sends_no_type():
    repo.reset()
    for name, declared in (("notes.md", ""), ("brief.txt", "application/octet-stream"), ("spec.markdown", "text/x-markdown")):
        response = client.post("/api/upload", files={"file": (name, b"# Brief\n\nCustomers need a saved basket.", declared)}, data={"user_id": "analyst"})
        assert response.status_code == 200, (name, response.text)
    assert {doc["file_type"] for doc in client.get("/api/documents").json()} == {"text/markdown", "text/plain"}
    unknown = client.post("/api/upload", files={"file": ("archive.zip", b"PK", "application/octet-stream")}, data={"user_id": "analyst"})
    assert unknown.status_code == 415


def test_missing_pdf_parser_is_an_error_not_indexed_text(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def without_pypdf(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    repo.reset()
    monkeypatch.setattr(builtins, "__import__", without_pypdf)
    response = client.post("/api/upload", files={"file": ("brief.pdf", b"%PDF-1.4", "application/pdf")}, data={"user_id": "analyst"})
    assert response.status_code == 422
    assert "pypdf" in response.json()["detail"]
    assert client.get("/api/documents").json() == []
