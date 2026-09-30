# AgentShield Lab — AI Security Playground

**Project 09 · runnable full product · offline-first**

![AgentShield Lab — AI Security Playground console with demo data loaded](docs/screenshot.png)

AgentShield Lab compares deliberately vulnerable and hardened agent behavior across six reproducible LLM-application threats. Every unsafe effect is confined to a synthetic in-memory tool sandbox. The hardened path returns policy IDs, ordered decisions, requested/executed tools, output encoding, and one-time approval evidence.

## Product workflow

1. Select direct injection, poisoned retrieval, active HTML, data leakage, excessive agency, or weak tool permissions.
2. Edit the payload and choose a learner, developer, or security-admin role.
3. Run either mode or compare both modes against the same input.
4. Inspect the decision trace, tool authorization, synthetic effect label, and approval state.
5. Run all 12 vulnerable/hardened checks and export the stored assessment as Markdown or JSON from the console.

On load, the console shows the latest stored assessment, run and approval counts, and the most recent vulnerable/hardened traces for the selected scenario, so existing evidence is visible without re-running it.

The deterministic rule engine works without an LLM key; no model generates output or verdicts. Verdicts depend on the input: a vulnerable run counts as a successful attack only when the payload actually carries the attack (an override phrase, active markup, a host-secret path, a mutating SQL statement, or a ticket request from a role that lacks the tool). The hardened path applies the scenario's role/tool matrix: a security admin may request a ticket, but the external write waits for one-time approval, and a single read-only `SELECT` is allowed.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=src uvicorn ai_security_playground_llm_applications.api.app:app --port 8010
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Alternatively, `docker compose up` starts both services. API docs are at `http://localhost:8010/docs`.

## Key API routes

- `GET /api/scenarios` — versioned threat and role/tool catalog
- `POST /api/execute/{id}` — custom or seeded execution
- `GET /api/runs` — recent redacted execution evidence
- `POST /api/approvals/{id}/resolve` and `/execute` — one-time approval lifecycle
- `POST /api/assessment` — complete red-team regression
- `GET /api/assessments?limit=` — stored assessments, newest first
- `GET /api/assessment/{id}/export?format=markdown|json`
- `GET /api/metrics`

## Verification

```bash
PYTHONPATH=src pytest -q
cd frontend && npm run build
```

Tests assert every attack/control pair, payload-dependent vulnerable verdicts, Unicode canonicalization, output encoding, role denial and admin approval gating, read-only SQL, assessment reconciliation and listing, approval resolution, and replay prevention.

## Safety boundary

Vulnerable mode is intentionally unsafe only in semantics. Its file, SQL, search, and ticket tools are synthetic fixtures and cannot access the host, network, credentials, or a real database. Hardened file access is virtual and allowlisted. Runs, approvals, and reports are kept in memory by default and persist when a database URL is configured (see [Persistence](#persistence)).

## Architecture

```mermaid
flowchart LR
  UI[React training console] --> API[FastAPI contracts]
  API --> CAT[Versioned scenario catalog]
  API --> V[Vulnerable synthetic path]
  API --> H[Hardened policy path]
  V --> S[Isolated synthetic tools]
  H --> S
  H --> A[One-time approvals]
  API --> R[Runs and assessment exports]
```

Additional design and demonstration material is in [`docs/`](docs/).

## Persistence

State is in memory by default, so the project runs with no setup. Set `AI_SECURITY_DATABASE_URL` to persist it:

```bash
AI_SECURITY_DATABASE_URL=sqlite:///./.local/state.sqlite3                          # single file
AI_SECURITY_DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<db>   # PostgreSQL
```

On startup the service restores its collections (`runs`, `reports`, `approvals`); after every successful write request it saves the documents that changed, and deletes removed ones, in one transaction. `docker compose up` uses SQLite on a named volume. For PostgreSQL, copy `.env.example` to `.env`, choose a `POSTGRES_PASSWORD`, and run `docker compose -f docker-compose.yml -f compose.postgres.yml up`; Compose refuses to start without the password, and no credential is committed. `tests/integration/test_persistence_restart.py` proves that state written by one process is served by a fresh process; set `PERSISTENCE_TEST_DATABASE_URL` to run it against PostgreSQL.
