"""State written in one process is served by a fresh process using the same database."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
# JSON-file state variables are removed so only the database can carry state across processes.
ISOLATED = ("RAG_STATE_DIR", "DATA_QUALITY_STATE_FILE", "CAPACITY_STATE_FILE", "DELIVERY_DESK_DB", "STOCKROOM_INVENTORY_DB")
HEADERS = {}


def database_url(tmp_path):
    """SQLite by default; PERSISTENCE_TEST_DATABASE_URL runs the same test against PostgreSQL."""
    url = os.getenv("PERSISTENCE_TEST_DATABASE_URL")
    if not url:
        return f"sqlite:///{tmp_path / 'state.sqlite3'}"
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS documents"))
    engine.dispose()
    return url


def run(database, statements):
    env = {key: value for key, value in os.environ.items() if key not in ISOLATED}
    env.update(PYTHONPATH=str(SRC), AGENTIC_BA_AUTOMATION_PLATFORM_DATABASE_URL=database)
    code = textwrap.dedent(f"""
        import json
        from fastapi.testclient import TestClient
        from agentic_ba_automation_platform.api.app import app
        with TestClient(app) as c:
            for response in [{", ".join(statements)}]:
                assert response.status_code < 400, response.text
            listing = c.get("/api/artifacts", headers={HEADERS!r})
            assert listing.status_code == 200, listing.text
            print(json.dumps(listing.json(), sort_keys=True))
    """)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_state_survives_a_restart(tmp_path):
    database = database_url(tmp_path)
    before = run(database, ['c.post("/api/demo/seed")'])
    assert before, "the write workflow should produce visible state"
    after = run(database, [])
    assert after == before


def test_without_a_database_url_state_stays_in_memory(tmp_path):
    env = {key: value for key, value in os.environ.items() if key not in ISOLATED and key != "AGENTIC_BA_AUTOMATION_PLATFORM_DATABASE_URL"}
    env["PYTHONPATH"] = str(SRC)
    code = "from agentic_ba_automation_platform.api.app import app; print(app.state.persistence is None)"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    assert result.stdout.strip().endswith("True"), result.stderr[-2000:]
