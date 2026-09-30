from io import BytesIO
from zipfile import ZipFile
import asyncio
import httpx
from internal_developer_portal_golden_paths.api.app import app

class ASGIClient:
    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
                return await session.request(method, path, **kwargs)
        return asyncio.run(send())
    def get(self, path, **kwargs): return self.request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self.request("POST", path, **kwargs)

client = ASGIClient()

def test_full_scaffold_flow():
    # 1. Health
    assert client.get("/health").status_code == 200
    
    # 2. List Templates (Acceptance criteria 1 requires 2 service types)
    resp_tpl = client.get("/api/templates")
    assert resp_tpl.status_code == 200
    templates = resp_tpl.json()
    assert len(templates) == 5
    assert any(t["id"] == "fastapi-base" for t in templates)
    assert any(t["id"] == "node-base" for t in templates)
    
    # 3. Scaffold a FastAPI service (Acceptance criteria 2, 3)
    fastapi_req = {
        "template_id": "fastapi-base",
        "service_name": "payments-api",
        "owner": "team-payments",
        "parameters": {
            "port": "8001"
        }
    }
    resp_scaffold1 = client.post("/api/scaffold", json=fastapi_req)
    assert resp_scaffold1.status_code == 200
    result1 = resp_scaffold1.json()
    assert result1["files_generated"] > 0
    assert "download_url" in result1
    assert len(result1["checksum_sha256"]) == 64

    manifest = client.get(result1["manifest_url"])
    assert manifest.status_code == 200
    assert manifest.json()["checksum_sha256"] == result1["checksum_sha256"]
    archive = client.get(result1["download_url"])
    assert archive.status_code == 200
    assert archive.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(archive.content)) as generated:
        paths = set(generated.namelist())
        assert {"main.py", "tests/test_main.py", "Dockerfile", "catalog-info.yaml"} <= paths
        assert "payments-api" in generated.read("main.py").decode()
    
    # 4. Scaffold a Node service
    node_req = {
        "template_id": "node-base",
        "service_name": "frontend-bff",
        "owner": "team-frontend",
        "parameters": {
            "port": "3000"
        }
    }
    resp_scaffold2 = client.post("/api/scaffold", json=node_req)
    assert resp_scaffold2.status_code == 200
    result2 = resp_scaffold2.json()
    assert result2["files_generated"] > 0
    
    # 5. Check Catalog (Acceptance criteria 4)
    resp_cat = client.get("/api/catalog")
    assert resp_cat.status_code == 200
    catalog = resp_cat.json()
    
    assert len(catalog) == 2
    
    payments_metadata = next(s for s in catalog if s["name"] == "payments-api")
    assert payments_metadata["owner"] == "team-payments"
    
    bff_metadata = next(s for s in catalog if s["name"] == "frontend-bff")
    assert bff_metadata["owner"] == "team-frontend"

    graph = client.get("/api/catalog/graph/dependencies")
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) == 2

def test_template_governance_and_validation():
    draft = {
        "id": "custom-api-v2", "name": "Custom API", "version": "2.0.0",
        "description": "Governed custom version", "status": "approved",
        "parameters": {"service_name": "string"}
    }
    assert client.post("/api/templates", json=draft).status_code == 403
    created = client.post("/api/templates", json=draft, headers={"x-role": "admin"})
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    approved = client.post(
        "/api/templates/custom-api-v2/approve",
        json={"reason": "Reviewed generated file contract"},
        headers={"x-role": "admin", "x-actor": "platform-lead"},
    )
    assert approved.status_code == 200
    assert approved.json()["approved_by"] == "platform-lead"

    invalid = client.post("/api/scaffold", json={
        "template_id": "fastapi-base", "service_name": "Unsafe_Name", "owner": "team-x", "parameters": {"port": "80"}
    })
    assert invalid.status_code == 400
