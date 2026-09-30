from internal_developer_portal_golden_paths.algorithms.template_engine import TemplateEngine
from internal_developer_portal_golden_paths.algorithms.quality_defaults import QualityDefaults

def test_fastapi_template():
    files = TemplateEngine.render_fastapi({"service_name": "auth", "port": "8080"})
    
    assert "main.py" in files
    assert "auth" in files["main.py"]
    assert "Dockerfile" in files
    assert "uvicorn" in files["Dockerfile"]
    assert "docker-compose.yml" in files
    assert "8080" in files["docker-compose.yml"]
    assert ".github/workflows/ci.yml" in files

def test_node_template():
    files = TemplateEngine.render_node({"service_name": "ui-bff", "port": "3000"})
    
    assert "index.js" in files
    assert "ui-bff" in files["index.js"]
    assert "Dockerfile" in files
    assert "node:22" in files["Dockerfile"]
    assert "package.json" in files
    assert "ui-bff" in files["package.json"]
    assert "test/health.test.js" in files

def test_every_golden_path_has_quality_defaults():
    for template_id in ["fastapi-base", "node-base", "react-base", "worker-base", "scheduled-job-base"]:
        files = TemplateEngine.render(template_id, {"service_name": "demo-service", "owner": "team-demo", "port": "8080"})
        assert "Dockerfile" in files
        assert "docker-compose.yml" in files
        assert ".github/workflows/ci.yml" in files
        assert "catalog-info.yaml" in files
        assert "README.md" in files
        assert any(path.startswith("test") for path in files)

def test_template_render_uses_request_identity():
    files = TemplateEngine.render_fastapi({"service_name": "billing-api", "owner": "team-billing", "port": "8010"})
    assert "billing-api" in files["main.py"]
    assert "team-billing" in files["catalog-info.yaml"]
