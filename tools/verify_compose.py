#!/usr/bin/env python3
"""Start every project with Docker Compose and check that it really serves.

For each project: ``docker compose up``, wait for the API health endpoint and
the console, then tear down with volumes. For projects with a PostgreSQL
overlay, also start ``api`` + ``postgres``, write data, restart the API
container, and confirm the data survived. Projects run one at a time because
several consoles share host ports.

Usage: python3 tools/verify_compose.py [project-slug ...]
"""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
# A write that creates visible state, and the listing that should show it.
PERSISTENCE_PROBES = {
    "agentic-ba-automation-platform": ("/api/demo/seed", "/api/artifacts"),
    "autonomous-data-quality-observatory": ("/api/demo/seed", "/api/sources"),
    "edge-wasm-plugin-runtime-data-network-rules": ("/api/demo/seed", "/api/plugins"),
    "local-ai-inference-gateway-llmops-console": ("/api/demo/seed", "/api/admin/templates"),
    "network-digital-twin-rl-routing-optimizer": ("/api/demo/seed", "/api/dashboard/experiments"),
    "real-time-fraud-risk-stream-analytics": ("/api/demo/seed", "/api/alerts"),
    "self-healing-public-data-intelligence-pipeline": ("/api/demo/seed", "/api/runs"),
    "smart-network-capacity-planner": ("/api/demo/seed", "/api/links"),
    "aiops-incident-assistant-human-approval": ("/api/incidents/generate", "/api/incidents"),
    "ai-security-playground-llm-applications": ("/api/execute/1?mode=hardened", "/api/runs"),
    "compliance-aware-rag-knowledge-base": ("/api/demo/seed", "/api/admin/documents"),
    "ai-code-review-test-gatekeeper": ("/api/reviews/local", "/api/dashboard/reports"),
    "internal-developer-portal-golden-paths": ("/api/scaffold", "/api/catalog"),
    "post-quantum-crypto-migration-scanner": ("/api/scan", "/api/dashboard"),
    "process-mining-workflow-automation-analyzer": ("/api/import/csv", "/api/reports"),
}
BODIES = {
    "/api/incidents/generate": {"type": "latency_spike", "service_name": "api-service"},
    "/api/reviews/local": {"id": "pr-compose", "repo": "user/quality", "title": "compose", "diff_content": "+const value = 1", "reported_coverage_percent": 72},
    "/api/scaffold": {"template_id": "fastapi-base", "service_name": "payments-api", "owner": "team-payments", "parameters": {"port": "8001"}},
    "/api/scan": [{"name": "legacy", "files": {"app.py": "import hashlib\nhashlib.md5(b'x')\n"}, "endpoints": []}],
    "/api/import/csv": {"content": "case_id,activity,timestamp,resource\nc1,Start,2026-01-01T00:00:00Z,intake\nc1,Done,2026-01-01T01:00:00Z,ops\n"},
}
RAG_ADMIN = {"X-User-ID": "admin-1", "X-User-Role": "admin", "X-User-Teams": "platform", "X-User-Clearance": "restricted"}


def compose(project: Path, *args: str, env: dict | None = None, files: tuple[str, ...] = ("docker-compose.yml",), timeout: int = 900):
    command = ["docker", "compose", "-p", f"verify-{project.name}"[:60]]
    for name in files:
        command += ["-f", name]
    return subprocess.run(command + list(args), cwd=project, env=env, capture_output=True, text=True, timeout=timeout)


def ports(project: Path) -> dict[str, int]:
    services = yaml.safe_load((project / "docker-compose.yml").read_text())["services"]
    found = {}
    for name in ("api", "frontend"):
        mapping = (services.get(name, {}).get("ports") or [None])[0]
        if mapping:
            found[name] = int(str(mapping).split(":")[0])
    return found


def request(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: float = 10):
    data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read()


def wait_for(url: str, deadline: float) -> tuple[bool, str]:
    last = ""
    while time.time() < deadline:
        try:
            status, _ = request(url, timeout=5)
            if status < 400:
                return True, ""
            last = f"HTTP {status}"
        except Exception as exc:  # noqa: BLE001 - startup errors are expected while waiting
            last = type(exc).__name__
        time.sleep(3)
    return False, last


def check_default(project: Path) -> str:
    found = ports(project)
    compose(project, "down", "-v", "--remove-orphans")
    started = compose(project, "up", "-d")
    if started.returncode:
        return "FAIL up: " + started.stderr.strip().splitlines()[-1]
    try:
        deadline = time.time() + 600
        ok, why = wait_for(f"http://127.0.0.1:{found['api']}/health", deadline)
        if not ok:
            logs = compose(project, "logs", "--tail", "15", "api").stdout
            return f"FAIL api health ({why})\n{logs}"
        if "frontend" in found:
            ok, why = wait_for(f"http://127.0.0.1:{found['frontend']}/", deadline)
            if not ok:
                logs = compose(project, "logs", "--tail", "15", "frontend").stdout
                return f"FAIL console ({why})\n{logs}"
        return "PASS api + console"
    finally:
        compose(project, "down", "-v", "--remove-orphans")


def check_postgres(project: Path) -> str:
    if not (project / "compose.postgres.yml").exists():
        return "skip (no postgres overlay)"
    files = ("docker-compose.yml", "compose.postgres.yml")
    env = {**__import__("os").environ, "POSTGRES_PASSWORD": secrets.token_urlsafe(18)}
    api_port = ports(project)["api"]
    compose(project, "down", "-v", "--remove-orphans", env=env, files=files)
    started = compose(project, "up", "-d", "api", "postgres", env=env, files=files)
    if started.returncode:
        return "FAIL postgres up: " + started.stderr.strip().splitlines()[-1]
    try:
        ok, why = wait_for(f"http://127.0.0.1:{api_port}/health", time.time() + 600)
        if not ok:
            return f"FAIL postgres api health ({why})\n" + compose(project, "logs", "--tail", "15", "api", env=env, files=files).stdout
        probe = PERSISTENCE_PROBES.get(project.name)
        if not probe:
            return "PASS postgres startup (no persistence probe)"
        write, read = probe
        headers = RAG_ADMIN if project.name.startswith("compliance") else {}
        request(f"http://127.0.0.1:{api_port}{write}", "POST", BODIES.get(write), headers, timeout=120)
        _, before = request(f"http://127.0.0.1:{api_port}{read}", headers=headers)
        compose(project, "restart", "api", env=env, files=files)
        ok, why = wait_for(f"http://127.0.0.1:{api_port}/health", time.time() + 600)
        if not ok:
            return f"FAIL postgres restart ({why})"
        _, after = request(f"http://127.0.0.1:{api_port}{read}", headers=headers)
        items = json.loads(before)
        if not items:
            return "FAIL postgres probe produced no data"
        return "PASS postgres + restart" if json.loads(after) == items else "FAIL data changed across restart"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL postgres probe: {type(exc).__name__}: {exc}"
    finally:
        compose(project, "down", "-v", "--remove-orphans", env=env, files=files)


def main(argv: list[str]) -> int:
    targets = [PROJECTS / name for name in argv] or sorted(p for p in PROJECTS.iterdir() if (p / "docker-compose.yml").exists())
    failures = 0
    for project in targets:
        started = time.time()
        results = [check_default(project), check_postgres(project)]
        failures += sum(result.startswith("FAIL") for result in results)
        print(f"{project.name}: {' | '.join(result.splitlines()[0] for result in results)} ({time.time() - started:.0f}s)", flush=True)
        for result in results:
            if result.startswith("FAIL") and "\n" in result:
                print("    " + result.split("\n", 1)[1].replace("\n", "\n    "), flush=True)
    print("All Compose checks passed." if not failures else f"{failures} Compose check(s) failed.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
