# Local portfolio delivery

## Implemented workspace

The portfolio runs at `http://127.0.0.1:3000` using `npm start`. It serves the portfolio, 19 project APIs, and 19 consoles from the same origin. There are no cloud services or model credentials required to try the default workflows.

The portfolio includes responsive navigation, four featured case studies, a searchable project index, discipline and saved filters, persistent saved projects, a persistent local notes form/viewer, project deep links, source browsing, README viewing, and live API health checks. Source browsing uses an explicit per-project allowlist and does not expose environment files or arbitrary filesystem paths.

## Showcase polish

- **Populated first visit:** `npm start` loads each product's own demo scenario into empty workspaces through its public API (`hub/demo.py`), so visitors do not land on empty consoles. Existing data is never replaced; `npm start -- --no-demo` starts empty.
- **Screenshots:** every product README opens with a screenshot of its console with demo data loaded (`docs/screenshot.png`).
- **Featured work:** the hub features Vaultline, Multi-Task PPO Lab, Quant Research Lab, and Delivery Desk.
- **No empty detail panels:** Tracework, OpsPilot, Riskstream, and Gatehouse open the first artifact, incident, alert, or review when data loads, and the Inference Gateway demo sends real requests through its offline provider so its metrics and request log are populated.
- **Code hygiene:** 88 unused imports removed across the products (pyflakes now reports only an intentional optional-dependency probe).

## Existing project improvements

- All 15 React consoles resolve API and asset paths inside the portfolio while retaining standalone use. Document titles identify the projects, and every embedded console has a return link.
- Requirements generation keeps the selected artifact current; approved JSON exports produce downloads.
- RAG and capacity forms retain their form references across asynchronous operations, avoiding post-submit crashes.
- Incident, fraud, review, gateway, and security consoles received fixes for stale selections, polling, request paths, and busy states.
- Fraud ingestion normalizes timestamps to UTC so browser events and seeded events can be processed together.
- BA GitHub export requires an explicit opt-in; inherited credentials alone cannot cause a remote write.
- Process import handles CSV byte-order marks, malformed input, and XES lifecycle information.
- Gateway chat and embedding requests honor the requested model and reject unknown models.
- Capacity telemetry batches validate completely before updating memory or persistent state.
- The Wasm project executes genuine modules through Wasmtime's `edge-json-v1` ABI. Each execution gets a fresh instance with fuel, memory, input/output, and deadline limits, and no host or WASI imports. A real example is available alongside the trusted adapters.

## Added projects

**Delivery Desk** demonstrates a persistent delivery board with task creation/editing, priorities, due dates, filters, activity history, and conflict-safe version checks. **Stockroom** demonstrates inventory creation, atomic stock movements, insufficient-stock rejection, idempotent requests, low-stock filtering, and ledger history. Both use FastAPI, SQLite, and responsive browser interfaces.

## Durable state for the original 15 projects

Each project's previously unused SQLAlchemy scaffolding is now a working adapter. `adapters/orm.py` defines one `documents` table keyed by `(collection, key)`; `adapters/database.py` restores registered collections at startup and, after each successful write request, saves only changed documents (by SHA-256 digest) and deletes removed ones in one transaction, so in-place edits are captured too. `api/persistence.py` lists each project's collections. `config.py` no longer carries default database credentials, Compose files no longer hard-code `portfolio/portfolio` passwords or start unused Redis containers, and URLs are redacted in logs. Gateway API keys are stored only as HMAC hashes and provider credentials are never serialized.

## Quant Research Lab

Consolidates three research scripts from earlier experiments (a stock-price ensemble, a crypto volatility study, and "The Architect" BTC signal) into one tested product with leak-free walk-forward evaluation, a cost-aware backtest, and risk analytics. See its README for the results and the list of corrected flaws.

## Multi-Task PPO Lab

A rewrite of the "AGI" reinforcement-learning experiment from earlier experiments, which could not learn (off-policy PPO from a replay buffer, an invisible goal, a stub second task). PPO with GAE is now implemented from scratch in PyTorch; one shared network learns navigation and key-and-door gridworlds. On 200 held-out layouts per task, the sampled policy solves 100% of navigation and 99.5% of key-and-door layouts, against 91.5% and 20.5% for a random agent, at 99% and 98% of optimal path efficiency. Training took 75 minutes on CPU; the checkpoint ships in `artifacts/`. Key-and-door efficiency rose from 85% to 98% after removing a misuse penalty that trapped exploration, bootstrapping truncated episodes, annealing the entropy bonus, and training longer.

## Verification

Verification is recorded from actual local commands, not inherited README claims. Last full run: 2026-09-30, after the product-by-product pass.

| Command | Result |
|---|---|
| `python3 tools/verify_portfolio.py` | 19 / 19 projects, 117 / 117 checks |
| `npm test` | 309 tests: 9 hub tests; 231 across the original 15 projects; 14 Delivery Desk, 15 Stockroom, 22 Quant Research Lab, and 18 Multi-Task PPO Lab tests |
| Standalone suites | 22 MIT OCW Smart Scraper, 11 NeuroFlow, and 28 ASP-1 tests |
| Restart persistence tests, SQLite | 15 / 15 projects |
| Restart persistence tests, PostgreSQL 16 in Docker | 15 / 15 projects |
| Fresh-clone check in clean `python:3.11-slim` and `node:22` containers (2026-09-29) | 19 / 19 product suites, hub, scraper (22 tests), 15 console builds, verifier, website build |
| `docker compose config --quiet` | 33 / 33 (18 base files, 15 PostgreSQL overlays); each overlay refuses to start without `POSTGRES_PASSWORD` |
| `python3 tools/verify_compose.py` | 19 / 19 projects start with `docker compose up` (API + console); 15 / 15 PostgreSQL overlays keep data across an API container restart |
| `npm run test:browser` | 5 / 5 hub checks with desktop and mobile screenshots |
| `npm run test:consoles` (isolated hub) | 30 / 30 console and workflow checks |
| `projects/run_all_frontend_checks.sh` | 15 / 15 React consoles lint and build |
| `npm run test:business` | 14 / 14 Delivery Desk and Stockroom checks, including persistence across a server restart |
| `npm run test:quant` | 8 / 8 Quant Research Lab checks, including CSV upload, keyboard tabs, a dataset switch during a run, and mobile layout |
| `npm run test:ppo` | 5 / 5 Multi-Task PPO Lab checks: curves, evaluation, animated replays, task switch, mobile layout |
| `npm run test:site` (in the published repository) | Overview site: data, interactions, and layout at desktop and phone widths |

The root API suite covers catalog/deep links, persistence, input validation, local request boundaries, source restrictions, static assets, and mounting every project.

## Product-by-product pass (2026-09-30)

Each product was reviewed on its own; highlights:

- **Correctness:** Quantum Ledger no longer reports post-quantum ML-DSA/SLH-DSA as classical DSA exposure and treats TLS 1.0 as critical; Gatehouse derives each analyzer's status from its findings (it previously showed secret and dependency scans as passed beside a hard-coded credential), detects unsafe deserialization, and keys duplicate detection on a stable digest; Vaultline's lexical scoring ignores stopwords and stems suffixes, so its showcase question now cites the right passage; AgentShield's vulnerable-mode verdicts depend on the input instead of always reporting success.
- **First views:** RouteLab, Pathfinder, AgentShield, the Inference Gateway, OpsPilot, FlowLens, and Quantum Ledger reopen their latest stored results through new read endpoints, so no console opens on empty panels.
- **Races and state:** Capacity Pilot, Quant Research Lab, and the PPO lab ignore stale responses; Tracework blocks approving text with unsaved edits; Riskstream recovers from a lost connection and refreshes an alert after a version conflict.
- **Honesty:** a hard-coded sparkline in Sourcewell became real per-run bars; placeholder metrics show "—" until there is data; documentation that described unbuilt components was rewritten to match the code.
- **Accessibility:** pressed and current states on toggles and navigation, labelled charts, keyboard tab navigation, and muted text raised to at least 4.5:1 contrast in Orbit and Capacity Pilot.

## Boundaries

- This is local development and local demonstration only; nothing was published or deployed.
- Docker: verified with Docker Desktop 29.8.1 (Compose v5.5.1) from WSL. `python3 tools/verify_compose.py` starts every project with `docker compose up`, waits for the API health endpoint and the console, and, for the 15 projects with a PostgreSQL overlay, writes data, restarts the API container, and confirms the data survived. Images are pulled public base images; nothing is pushed or deployed.
- Notes are stored locally and are not emailed. Public contact uses the explicit `mailto:` link.
- Saved projects, notes, Delivery Desk, and Stockroom persist by default. The 15 original projects keep state in memory by default and persist to SQLite or PostgreSQL when their `<PREFIX>DATABASE_URL` is set. Quant Research Lab keeps uploads in memory.
- Default AI outputs use the documented deterministic/offline implementations. External providers, production authentication, cloud infrastructure, and external delivery were not verified.
- The source viewer exposes code and documentation, not repository credentials.
- The shared server runs a single process. It is intended for trusted loopback use; production concurrency, isolation, identity, and deployment require further work.
