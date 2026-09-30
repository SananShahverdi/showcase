# Sanan Shahverdi · Software portfolio

Full-stack and machine-learning engineering, shipped as software you can run: **19 products** served from one local hub, plus **four standalone projects**. Every product has its own API, interface, documentation, and tests. Learned models are measured against baselines on data they have not seen.

**[Interactive overview](https://sananshahverdi.github.io/showcase/)** · **[CV (PDF)](cv/Sanan_Shahverdi_CV.pdf)** · [CV (Markdown)](cv/Sanan_Shahverdi_CV.md)

| Highlight | Result |
|---|---|
| [Multi-Task PPO Lab](projects/multitask-ppo-lab/) | PPO from scratch; one network solves 99.5% of unseen key-and-door layouts at 98.4% of optimal path length |
| [NeuroFlow](standalone/neuroflow/) | At 110% bottleneck load, load-aware routing keeps delay at 18 time units while shortest paths reach 408 |
| [ASP-1](standalone/asp-1/) | A deep-space probe decides when to navigate: uncertainty-triggered fixes match a fixed schedule's tail error with 43% fewer fixes; downlink 13.8× smaller than raw, lossless |
| [Quant Research Lab](projects/quant-research-lab/) | Walk-forward forecasting with significance tests; reports honestly that no model beats a random walk |
| [Portfolio hub](hub/) | 19 products, 300 product tests, all verified under Docker Compose and PostgreSQL restarts |

## Repository layout

```text
.
├── hub/, web/              Portfolio hub: catalog, case studies, source reader, live status
├── projects/               19 products (FastAPI back ends, React or build-free consoles)
├── standalone/
│   ├── neuroflow/               Queueing-network simulator: learned versus static routing under load
│   ├── asp-1/                   Deep-space probe autonomy: sleep, navigation fixes, and downlink under tight budgets
│   ├── mit-ocw-smart-scraper/   Command-line course archiver for MIT OpenCourseWare
│   └── effekt-website/          Production marketing site (React, Three.js, three languages)
├── site/                   Static overview published to GitHub Pages
├── cv/                     CV in Markdown and PDF, with its renderer
├── docs/                   Delivery report: what was verified, and how
├── tests/, tools/          Hub tests, verifiers, browser and Docker checks
└── .github/workflows/      Continuous integration and Pages deployment
```

Folder names describe each product's domain; the product names in the table below are the brands shown in each console.

## Quick start

Python 3.11+ and Node 22.12+:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-local.txt --extra-index-url https://download.pytorch.org/whl/cpu
npm ci
npm run build        # builds the 15 React consoles for the hub
npm start            # http://127.0.0.1:3000, with demo data loaded into empty projects
```

`npm start -- --no-demo` starts with empty workspaces. Any single product also runs on its own: see its README, or `docker compose up` in its folder.

## Products

| Product | What it demonstrates |
|---|---|
| [Vaultline](projects/compliance-aware-rag-knowledge-base/) | Retrieval with access control before ranking, exact citations, and abstention |
| [Tracework](projects/agentic-ba-automation-platform/) | Source-cited requirements artifacts with an explicit review workflow |
| [Inference Gateway](projects/local-ai-inference-gateway-llmops-console/) | Provider routing, fallback, API keys, quotas, and prompt versions |
| [Multi-Task PPO Lab](projects/multitask-ppo-lab/) | PPO written from scratch; one network learns two tasks, evaluated on unseen layouts |
| [Quant Research Lab](projects/quant-research-lab/) | Leak-free walk-forward forecasting, a cost-aware backtest, and GARCH risk analytics |
| [Orbit](projects/autonomous-data-quality-observatory/) | Data profiling, baseline drift detection, and deduplicated incidents |
| [Sourcewell](projects/self-healing-public-data-intelligence-pipeline/) | Extraction quarantine, DOM-drift detection, and human-approved repairs |
| [Riskstream](projects/real-time-fraud-risk-stream-analytics/) | Event-time features, explainable risk scores, and analyst feedback |
| [FlowLens](projects/process-mining-workflow-automation-analyzer/) | Process discovery, variants, SLA breaches, and rework from event logs |
| [OpsPilot](projects/aiops-incident-assistant-human-approval/) | Evidence-grounded remediation plans behind human approval |
| [Gatehouse](projects/ai-code-review-test-gatekeeper/) | Diff analysis with severity, test, and coverage policies |
| [Pathfinder](projects/internal-developer-portal-golden-paths/) | Deterministic service scaffolds with checksums and a service catalog |
| [AgentShield Lab](projects/ai-security-playground-llm-applications/) | Vulnerable versus hardened behavior across six LLM application threats |
| [Quantum Ledger](projects/post-quantum-crypto-migration-scanner/) | Evidence-backed cryptographic inventory and post-quantum migration ranking |
| [EdgeForge](projects/edge-wasm-plugin-runtime-data-network-rules/) | WebAssembly plugins under fuel, memory, and deadline limits, with canary and rollback |
| [RouteLab](projects/network-digital-twin-rl-routing-optimizer/) | Network simulation with tabular Q-learning compared against baselines |
| [Capacity Pilot](projects/smart-network-capacity-planner/) | Explainable capacity forecasts, saturation risk, and budget-aware actions |
| [Delivery Desk](projects/delivery-desk/) | Persistent task board with change history and optimistic concurrency |
| [Stockroom](projects/stockroom-inventory/) | Transactional inventory with an append-only ledger and idempotent movements |

Standalone: [NeuroFlow](standalone/neuroflow/) simulates a network of queues and shows when learned Q-routing beats shortest-path routing as load approaches saturation; [ASP-1](standalone/asp-1/) simulates a power-starved deep-space probe that decides when to navigate and what to downlink, with a statistically consistent Kalman filter and a model-coded, lossless telemetry gate; [MIT OCW Smart Scraper](standalone/mit-ocw-smart-scraper/) archives courses into structured folders and a single merged PDF with captions and transcripts; [Effekt website](standalone/effekt-website/) is a multilingual portfolio site for bath, wellness, sauna, and pool work.

## Engineering notes

- **Persistence:** the 15 original products keep state in memory by default and persist to SQLite or PostgreSQL when their `<PREFIX>DATABASE_URL` is set, through a shared SQLAlchemy unit-of-work adapter. Delivery Desk and Stockroom use SQLite directly.
- **Docker:** every product has a Compose file; the 15 originals also have a PostgreSQL overlay (`compose.postgres.yml`) whose password comes from a git-ignored `.env`.
- **Honest scope:** simulations, synthetic data, and offline providers are labeled in each console and README. Nothing here is presented as production-deployed.

## Verify

```bash
python3 tools/verify_portfolio.py    # structure, docs, Compose files, console builds
npm test                             # hub tests and every product's test suite
npm run test:browser                 # hub browser checks
python3 tools/verify_compose.py      # docker compose up for every product, PostgreSQL restarts
npm run test:site                    # overview site: data, interactions, desktop and mobile layout
```

[docs/delivery-report.md](docs/delivery-report.md) records the most recent verification results, and [projects/README.md](projects/README.md) indexes the products.

## Overview site

`site/` is plain HTML, CSS, and JavaScript with no build step. `python3 site/build_data.py` regenerates its data from the projects themselves (PPO episode replays, forecast scores, simulation results, screenshots), and the Pages workflow publishes it on every push to `main` that changes it.

## Local architecture

```text
Browser → 127.0.0.1:3000
  /                         Portfolio interface
  /projects/<slug>          Case study
  /demos/<slug>/            Product console
  /api/projects/<slug>/api  That product's API
  /api/projects/<slug>/docs Interactive API reference
```

This is a single-user workspace bound to loopback. Demo identity headers and admin consoles are not public authentication.

## License

Copyright (C) 2026 Sanan Shahverdi.

This repository, including the standalone projects, is licensed under the GNU General Public License v3.0; see [LICENSE](LICENSE). You may use, study, change, and share it, but any distributed modified version must also be released under GPL-3.0 with its source code.
