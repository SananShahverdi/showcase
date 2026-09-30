"""Exercise persistence, validation, source boundaries, and mounted APIs."""
import pytest
from fastapi.testclient import TestClient

from hub.app import create_app
from hub.catalog import PROJECTS


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, mount_projects=False)) as instance:
        yield instance


def test_catalog_and_deep_links(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 19
    assert len({item["slug"] for item in projects}) == len(projects)
    assert all("module" not in item for item in projects)
    assert client.get("/projects/delivery-desk").status_code == 200
    assert client.get("/projects/missing").status_code == 404


def test_saved_projects_are_durable_idempotent_and_removable(tmp_path):
    first = TestClient(create_app(tmp_path, mount_projects=False))
    slug = PROJECTS[0]["slug"]
    for _ in range(2):
        response = first.put(f"/api/saved/{slug}", json={"saved": True})
        assert response.json()["saved"] == [slug]
    second = TestClient(create_app(tmp_path, mount_projects=False))
    assert second.get("/api/projects").json()["saved"] == [slug]
    assert second.put(f"/api/saved/{slug}", json={"saved": False}).json()["saved"] == []
    assert first.get("/api/projects").json()["saved"] == []
    assert first.put("/api/saved/missing", json={"saved": True}).status_code == 404


def test_notes_validate_and_survive_new_app_instance(tmp_path):
    first = TestClient(create_app(tmp_path, mount_projects=False))
    content = {"name": "  Local reviewer  ", "email": "review@example.com", "message": "Keep the source viewer easy to find."}
    response = first.post("/api/notes", json=content)
    assert response.status_code == 201
    assert response.json()["name"] == "Local reviewer"
    assert response.json()["id"] == 1
    second = TestClient(create_app(tmp_path, mount_projects=False))
    assert second.get("/api/notes").json()[0]["message"] == content["message"]
    for invalid in [{"email": "bad"}, {"message": " " * 15}, {"name": " " * 5}, {"message": "x" * 3001}, {"admin": True}]:
        assert first.post("/api/notes", json=content | invalid).status_code == 422
    assert len(second.get("/api/notes").json()) == 1


def test_local_origin_and_host_boundary(client):
    payload = {"saved": True}
    url = "/api/saved/delivery-desk"
    assert client.put(url, json=payload, headers={"Origin": "https://unrelated.example"}).status_code == 403
    assert client.put(url, json=payload, headers={"Origin": "http://testserver", "Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.put(url, json=payload, headers={"Origin": "http://testserver"}).status_code == 200
    assert client.get("/health", headers={"Host": "unrelated.example"}).status_code == 400
    assert client.get("/api/projects").headers["Cache-Control"] == "no-store"


def test_source_viewer_uses_explicit_allowlist(client):
    prefix = "/api/projects/compliance-aware-rag-knowledge-base"
    paths = client.get(prefix + "/files").json()["files"]
    assert any(path.endswith("api/app.py") for path in paths)
    response = client.get(prefix + "/source", params={"path": paths[0]})
    assert response.status_code == 200
    assert response.json()["path"] == paths[0]
    for path in ["../../../../.aws/credentials", ".env", "frontend/../../../package.json", "/etc/passwd"]:
        assert client.get(prefix + "/source", params={"path": path}).status_code == 404
    assert client.get(prefix + "/readme").json()["content"].startswith("# Compliance")


def test_static_assets_and_traversal(client):
    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/%2e%2e/package.json").status_code == 404
    assert client.get("/demos/delivery-desk/%2e%2e/%2e%2e/README.md").status_code == 404


def test_all_project_apps_mount_and_health_check(tmp_path):
    app = create_app(tmp_path)
    assert app.state.failures == {}
    with TestClient(app) as client:
        assert client.get("/health").json()["projects_loaded"] == len(PROJECTS)
        status = client.get("/api/status").json()["projects"]
        assert len(status) == len(PROJECTS)
        assert all(item["status"] == "ready" for item in status.values())
        for project in PROJECTS:
            prefix = project["api_url"]
            assert client.get(prefix + "/health").status_code == 200, project["slug"]
            assert client.get(prefix + "/openapi.json").status_code == 200, project["slug"]
        # Route integration, including OpenAI-compatible gateway and genuine Wasmtime capability.
        assert client.get("/api/projects/local-ai-inference-gateway-llmops-console/v1/models").status_code == 200
        assert client.get("/api/projects/edge-wasm-plugin-runtime-data-network-rules/api/runtime/capabilities").status_code == 200


def test_demo_listing_emptiness():
    from hub.demo import is_empty
    assert is_empty([]) and is_empty({"items": [], "projects": []})
    assert not is_empty([1]) and not is_empty({"items": [1], "counts": {}})
    assert not is_empty({"status": "ok"})  # no list: cannot tell, so never seed over it


def test_demo_seeding_only_fills_empty_projects():
    import asyncio

    from fastapi import FastAPI

    from hub.demo import seed_demos

    def fake(initial):
        app, items = FastAPI(), list(initial)

        @app.get("/api/tasks")
        def listing():
            return {"items": items}

        @app.post("/api/demo/seed")
        def seed():
            items.append("sample")
            return {"added": 1}

        return app, items

    empty_app, empty_items = fake([])
    busy_app, busy_items = fake(["mine"])
    outcomes = asyncio.run(seed_demos({"delivery-desk": empty_app}))
    assert outcomes == {"delivery-desk": "seeded"} and empty_items == ["sample"]
    outcomes = asyncio.run(seed_demos({"delivery-desk": busy_app}))
    assert outcomes == {"delivery-desk": "kept existing data"} and busy_items == ["mine"]
