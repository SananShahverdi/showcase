# Full-stack application and systems portfolio

This workspace contains **19 local products**: 15 AI, data, platform, security, and network projects, plus Delivery Desk, Stockroom, Quant Research Lab, and Multi-Task PPO Lab. All are connected to the [local portfolio application](../README.md): run `npm start` from the portfolio root and open `http://127.0.0.1:3000`.

The original 15 projects have FastAPI backends, React consoles, sample-data workflows, tests, and standalone Compose configurations. The three newer products use FastAPI and build-free browser modules (Delivery Desk and Stockroom on SQLite), and run through the portfolio, their standalone commands, or their own Compose files. Their scope and storage behavior are explicit in their READMEs.

“Full viable” here means useful and complete in its documented local scope. It does **not** mean these systems are claimed as production-deployed. External models, cloud services, brokers, scanners, and provider APIs are real optional adapters or explicitly labeled offline/synthetic implementations—never fabricated successes.

## Current verification

| Gate | Result |
|---|---:|
| Projects passing static verification | 19 / 19 (117 checks) |
| Backend project suites | 19 / 19 |
| Backend tests, original 15 projects | 204 / 204 |
| Backend tests, Delivery Desk, Stockroom, Quant Research Lab, Multi-Task PPO Lab | 68 / 68 |
| Portfolio hub API tests | 9 / 9 |
| Restart persistence tests on SQLite and on PostgreSQL 16 | 15 / 15 each |
| Frontend production builds and lint (React consoles) | 15 / 15 |
| `docker compose config` validation (base files and Postgres overlays) | 33 / 33 |
| `docker compose up`: API and console respond | 19 / 19 |
| PostgreSQL overlay: data survives an API container restart | 15 / 15 |
| Console workflow browser checks | 30 / 30 |
| Delivery Desk and Stockroom browser checks | 14 / 14 |
| Quant Research Lab browser checks | 6 / 6 |
| Multi-Task PPO Lab browser checks | 5 / 5 |
| Portfolio hub browser checks | 5 / 5 |

See [current local delivery evidence](../docs/delivery-report.md).

## Products

### Product engineering

16. **[Delivery Desk](delivery-desk/)** — persistent task board with priorities, due dates, filtering, edit history, and optimistic concurrency protection.
17. **[Stockroom](stockroom-inventory/)** — inventory catalog, atomic receiving/dispatch, insufficient-stock checks, idempotent movement requests, low-stock visibility, and an immutable ledger.
18. **[Quant Research Lab](quant-research-lab/)** — point-in-time features, walk-forward forecasts scored against a random walk with Diebold-Mariano tests, a cost-aware signal backtest, and VaR/GARCH/Hurst risk analytics on real AAPL and BTC data.
19. **[Multi-Task PPO Lab](multitask-ppo-lab/)** — PPO with GAE written from scratch in PyTorch; one shared network learns gridworld navigation and a key-and-door task, evaluated on held-out layouts against random and optimal (BFS) play, with a replay console.

### AI and knowledge systems

1. **[Agentic BA Automation Platform](agentic-ba-automation-platform/)** — ingests stakeholder evidence, produces six source-cited artifact types, enforces edit/reject/approve transitions, and exports approved work.
2. **[Local AI Inference Gateway and LLMOps Console](local-ai-inference-gateway-llmops-console/)** — OpenAI-compatible routing across real Ollama/OpenAI-compatible adapters and a clearly labeled deterministic offline provider, with keys, quotas, prompt versions, privacy, fallback, and attempt evidence.
3. **[Compliance-Aware RAG Knowledge Base](compliance-aware-rag-knowledge-base/)** — filters status, expiry, clearance, role, and team before hybrid retrieval; returns exact cited evidence or abstains; includes lifecycle, redaction, feedback, audit, and golden evaluation.

### Data engineering and analytics

4. **[Self-Healing Public Data Intelligence Pipeline](self-healing-public-data-intelligence-pipeline/)** — performs real fixture/HTTPS extraction, typed validation, quarantine, DOM drift detection, repair replay, and human-approved recipe activation.
5. **[Real-Time Fraud and Risk Stream Analytics](real-time-fraud-risk-stream-analytics/)** — computes bounded event-time features, explainable risk, watermark/duplicate handling, alert triage, feedback export, and drift/precision metrics.
6. **[Process Mining and Workflow Automation Analyzer](process-mining-workflow-automation-analyzer/)** — imports JSON/CSV/safe XML event logs and calculates transitions, variants, percentiles, SLA breaches, rework, resource/handoff evidence, and grounded automation recommendations.
7. **[Autonomous Data Quality Observatory](autonomous-data-quality-observatory/)** — reads real bounded CSV/JSON/inline data, profiles history, evaluates seven rule families, detects baseline drift, scores health, and manages deduplicated incidents.

### Platform engineering and operations

8. **[AIOps Incident Assistant with Human Approval](aiops-incident-assistant-human-approval/)** — turns repeatable telemetry scenarios into evidence-grounded plans, blocks unsafe actions, requires human decisions, executes only catalogued local actions, and exports post-incident evidence.
9. **[AI Code Review and Test Gatekeeper](ai-code-review-test-gatekeeper/)** — parses unified diffs, normalizes findings, applies severity/test/coverage policies, deduplicates deliveries, and exposes review and recurring-risk analytics.
10. **[Internal Developer Portal with Golden Paths](internal-developer-portal-golden-paths/)** — renders and downloads deterministic service ZIPs with checksums, real CI/tests, catalog ownership/dependencies, and governed template versions.

### Security and edge

11. **[AI Security Playground for LLM Applications](ai-security-playground-llm-applications/)** — compares vulnerable and hardened behavior across six threats using a confined synthetic tool sandbox, policy traces, approvals, and assessment exports.
12. **[Post-Quantum Crypto Migration Scanner](post-quantum-crypto-migration-scanner/)** — builds an evidence-backed cryptographic inventory from bounded source/config/TLS observations and ranks quantum migration work without inventing live endpoint results.
13. **[Edge Wasm Plugin Runtime](edge-wasm-plugin-runtime-data-network-rules/)** — validates real Wasm structure, versions/quarantines artifacts, gates canaries, performs compare-and-set activation/rollback, and labels local adapter versus Wasmtime provenance.

### Network intelligence

14. **[Network Digital Twin and RL Routing Optimizer](network-digital-twin-rl-routing-optimizer/)** — simulates directed networks, trains actual tabular Q-learning, compares it fairly with deterministic baselines, and replays link failures with versioned experiment evidence.
15. **[Smart Network Capacity Planner](smart-network-capacity-planner/)** — validates multi-link telemetry, fits explainable trend forecasts with uncertainty, scores saturation, ranks budget-aware actions, compares saved scenarios, and exports weekly reports.

## Run one product

Every project is independent:

```bash
cd projects/<project-slug>
docker compose up
```

Use the ports documented in that project's README. For a non-Docker setup:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=src python3 -m pytest -q
```

Then build the console:

```bash
cd frontend
npm install
npm run build
npm run dev
```

## Verify the portfolio

From the repository root:

```bash
python3 tools/verify_portfolio.py
npm test                 # hub plus all 19 backend suites, isolated state
npm run test:browser     # hub browser checks
npm run test:business    # Delivery Desk and Stockroom browser checks
npm run test:quant       # Quant Research Lab browser checks
npm run test:ppo         # Multi-Task PPO Lab browser checks
python3 tools/verify_compose.py   # docker compose up for every project, plus PostgreSQL restarts
cd projects && ./run_all_frontend_checks.sh
```

`npm run test:consoles` drives all 15 React consoles against a running hub (`npm start` first, or set `PORTFOLIO_URL`). It seeds demo data, so point it at a throwaway instance rather than one holding data you care about.

The verifier parses all Compose files, checks documentation structure and test modules, rejects Vite starter markers, requires production build artifacts for React consoles, and checks that build-free consoles load their browser module.

## Architecture and evidence policy

- Each product keeps domain, algorithm/service, repository/adapter, API, and UI concerns separable.
- State is in memory by default so everything runs without infrastructure. Each of the 15 original projects persists to SQLite or PostgreSQL when its `<PREFIX>DATABASE_URL` is set, through a shared SQLAlchemy unit-of-work adapter; Compose uses SQLite by default and `compose.postgres.yml` switches to PostgreSQL with a password supplied from a git-ignored `.env`.
- AI-assisted narratives are deterministic and evidence-bound unless a real provider is configured.
- Human approval remains explicit where automation could affect infrastructure, code integration, access, or operations.
- Synthetic inputs, simulation, offline providers, and local adapters are labeled at the API/UI and in documentation.

Shared contribution and security expectations are in [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
