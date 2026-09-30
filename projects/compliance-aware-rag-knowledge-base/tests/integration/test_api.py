import httpx
import pytest

from compliance_aware_rag_knowledge_base.api.app import app

ADMIN = {"X-User-ID": "admin", "X-User-Role": "admin", "X-User-Teams": "security,product,general", "X-User-Clearance": "restricted"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_governed_api_journey():
  async with client() as api:
    assert (await api.get("/health")).status_code == 200
    seeded = await api.post("/api/demo/seed", headers=ADMIN)
    assert seeded.status_code == 200
    assert seeded.json()["created_count"] >= 0

    employee = {"X-User-ID": "maya", "X-User-Role": "employee", "X-User-Teams": "product,general", "X-User-Clearance": "internal"}
    answer = await api.post("/api/query", json={"text": "When does Project Atlas launch?"}, headers=employee)
    assert answer.status_code == 200
    assert "Q3 2026" in answer.json()["text"]
    assert answer.json()["citations"]

    contractor = {"X-User-ID": "vendor", "X-User-Role": "contractor", "X-User-Teams": "general", "X-User-Clearance": "internal"}
    denied = await api.post("/api/query", json={"text": "When is the emergency credential rotation?"}, headers=contractor)
    assert denied.status_code == 200
    assert denied.json()["abstained"] is True
    assert denied.json()["citations"] == []

    assert (await api.get("/api/admin/documents", headers=contractor)).status_code == 403
    documents = await api.get("/api/admin/documents", headers=ADMIN)
    assert documents.status_code == 200
    assert all("content" not in item for item in documents.json())

    feedback = await api.post(f"/api/answers/{answer.json()['id']}/feedback", json={"rating": 5, "reason": "Good citations"}, headers=employee)
    assert feedback.status_code == 201
    audit = await api.get("/api/admin/audit", headers=ADMIN)
    assert audit.status_code == 200
    assert any(event["event_type"] == "feedback_recorded" for event in audit.json())


@pytest.mark.anyio
async def test_upload_validation_and_real_soft_delete_restore():
  async with client() as api:
    uploaded = await api.post(
        "/api/ingest", headers=ADMIN,
        files={"file": ("policy.md", b"# Leave policy\nEmployees receive twenty days annual leave.", "text/markdown")},
        data={"title": "Leave policy", "allowed_roles": "employee,admin", "allowed_teams": "general", "sensitivity": "internal"},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["document"]["id"]
    deleted = await api.delete(f"/api/admin/documents/{document_id}", headers=ADMIN)
    assert deleted.json()["status"] == "deleted"
    restored = await api.post(f"/api/admin/documents/{document_id}/restore", headers=ADMIN)
    assert restored.json()["status"] == "active"

    unsupported = await api.post(
        "/api/ingest", headers=ADMIN,
        files={"file": ("image.png", b"not-an-image", "image/png")},
        data={"title": "Bad", "allowed_roles": "employee"},
    )
    assert unsupported.status_code == 400
