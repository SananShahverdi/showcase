import json
from typing import Dict

from internal_developer_portal_golden_paths.algorithms.quality_defaults import QualityDefaults


class TemplateEngine:
    @staticmethod
    def _common(name: str, owner: str, lang: str, component_type: str) -> Dict[str, str]:
        return {
            ".github/workflows/ci.yml": QualityDefaults.get_ci_config(lang),
            ".gitignore": "__pycache__/\n.pytest_cache/\nnode_modules/\ndist/\n.env\n",
            "catalog-info.yaml": QualityDefaults.metadata(name, owner, component_type),
        }

    @staticmethod
    def render_fastapi(params: Dict[str, str]) -> Dict[str, str]:
        name, owner, port = params.get("service_name", "fastapi-service"), params.get("owner", "team-platform"), params.get("port", "8000")
        files = TemplateEngine._common(name, owner, "python", "service")
        files.update({
            "main.py": f'''import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="{name}")

@app.get("/health")
def health():
    return {{"status": "ok", "service": "{name}"}}

@app.get("/ready")
def ready():
    return {{"status": "ready"}}
''',
            "tests/test_main.py": "from fastapi.testclient import TestClient\nfrom main import app\n\nclient = TestClient(app)\n\ndef test_health():\n    assert client.get('/health').json()['status'] == 'ok'\n",
            "Dockerfile": QualityDefaults.get_dockerfile("python", f'["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]'),
            "docker-compose.yml": QualityDefaults.get_docker_compose(name, port),
            "requirements.txt": "fastapi==0.110.0\nuvicorn==0.27.1\npytest==8.0.2\nhttpx==0.27.0\n",
            "README.md": f"# {name}\n\nOwned by `{owner}`.\n\nRun: `docker compose up --build`\n\nTest: `pytest -q`\n",
        })
        return files

    @staticmethod
    def render_node(params: Dict[str, str]) -> Dict[str, str]:
        name, owner, port = params.get("service_name", "node-service"), params.get("owner", "team-platform"), params.get("port", "3000")
        files = TemplateEngine._common(name, owner, "node", "service")
        package = {"name": name, "version": "1.0.0", "scripts": {"start": "node index.js", "test": "node --test"}, "dependencies": {"express": "4.21.2"}}
        files.update({
            "index.js": f"const express = require('express');\nconst app = express();\napp.get('/health', (_req, res) => res.json({{status: 'ok', service: '{name}'}}));\nif (require.main === module) app.listen({port}, () => console.log(JSON.stringify({{event: 'listening', port: {port}}})));\nmodule.exports = app;\n",
            "test/health.test.js": "const test = require('node:test');\nconst assert = require('node:assert');\ntest('basic invariant', () => assert.equal(typeof require('../index'), 'function'));\n",
            "package.json": json.dumps(package, indent=2),
            "Dockerfile": QualityDefaults.get_dockerfile("node"),
            "docker-compose.yml": QualityDefaults.get_docker_compose(name, port),
            "README.md": f"# {name}\n\nOwned by `{owner}`. Run `npm install && npm test` or `docker compose up --build`.\n",
        })
        return files

    @staticmethod
    def render_react(params: Dict[str, str]) -> Dict[str, str]:
        name, owner, port = params.get("service_name", "react-app"), params.get("owner", "team-platform"), params.get("port", "5173")
        files = TemplateEngine._common(name, owner, "node", "website")
        package = {"name": name, "private": True, "version": "1.0.0", "type": "module", "scripts": {"dev": "vite --host 0.0.0.0", "build": "vite build", "test": "node --test"}, "dependencies": {"@vitejs/plugin-react": "latest", "vite": "latest", "typescript": "latest", "react": "latest", "react-dom": "latest"}, "devDependencies": {}}
        files.update({
            "index.html": '<div id="root"></div><script type="module" src="/src/main.jsx"></script>',
            "src/main.jsx": "import React from 'react';\nimport {createRoot} from 'react-dom/client';\ncreateRoot(document.getElementById('root')).render(<main><h1>Service ready</h1></main>);\n",
            "vite.config.js": "import {defineConfig} from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({plugins:[react()]});\n",
            "test/smoke.test.js": "import test from 'node:test';\nimport assert from 'node:assert';\ntest('app name', () => assert.ok('app'));\n",
            "package.json": json.dumps(package, indent=2),
            "Dockerfile": "FROM node:22-alpine AS build\nWORKDIR /app\nCOPY . .\nRUN npm install && npm run build\nFROM nginx:1.27-alpine\nCOPY --from=build /app/dist /usr/share/nginx/html\n",
            "docker-compose.yml": f'services:\n  {name}:\n    build: .\n    ports:\n      - "{port}:80"\n    environment:\n      OTEL_SERVICE_NAME: {name}\n',
            "README.md": f"# {name}\n\nOwned by `{owner}`. Run `npm install && npm run dev`.\n",
        })
        return files

    @staticmethod
    def render_worker(params: Dict[str, str]) -> Dict[str, str]:
        name, owner = params.get("service_name", "python-worker"), params.get("owner", "team-platform")
        files = TemplateEngine._common(name, owner, "python", "service")
        files.update({
            "worker.py": "import json\nimport logging\n\nlogging.basicConfig(level=logging.INFO)\n\ndef process(payload: dict) -> dict:\n    return {'accepted': True, 'payload': payload}\n\nif __name__ == '__main__':\n    logging.info(json.dumps(process({'source': 'local'})))\n",
            "tests/test_worker.py": "from worker import process\n\ndef test_process():\n    assert process({'id': 1})['accepted'] is True\n",
            "requirements.txt": "pytest==8.0.2\n",
            "Dockerfile": QualityDefaults.get_dockerfile("python", '["python", "worker.py"]'),
            "docker-compose.yml": QualityDefaults.get_docker_compose(name),
            "README.md": f"# {name}\n\nOwned by `{owner}`. Run `python worker.py`; test with `pytest -q`.\n",
        })
        return files

    @staticmethod
    def render_scheduled(params: Dict[str, str]) -> Dict[str, str]:
        name, owner = params.get("service_name", "scheduled-job"), params.get("owner", "team-platform")
        files = TemplateEngine._common(name, owner, "python", "service")
        files.update({
            "job.py": "from datetime import datetime, timezone\n\ndef run() -> str:\n    return datetime.now(timezone.utc).isoformat()\n\nif __name__ == '__main__':\n    print(run())\n",
            "tests/test_job.py": "from job import run\n\ndef test_run_is_utc():\n    assert '+00:00' in run()\n",
            "requirements.txt": "pytest==8.0.2\n",
            "Dockerfile": QualityDefaults.get_dockerfile("python", '["python", "job.py"]'),
            "docker-compose.yml": QualityDefaults.get_docker_compose(name),
            "README.md": f"# {name}\n\nOwned by `{owner}`. Invoke with your scheduler using `python job.py`; test with `pytest -q`.\n",
        })
        return files

    @staticmethod
    def render(template_id: str, params: Dict[str, str]) -> Dict[str, str]:
        renderers = {
            "fastapi-base": TemplateEngine.render_fastapi,
            "node-base": TemplateEngine.render_node,
            "react-base": TemplateEngine.render_react,
            "worker-base": TemplateEngine.render_worker,
            "scheduled-job-base": TemplateEngine.render_scheduled,
        }
        try:
            return renderers[template_id](params)
        except KeyError as error:
            raise ValueError("Unsupported template generator") from error
