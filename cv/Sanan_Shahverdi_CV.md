# Sanan Shahverdi

**Full-stack & machine-learning engineer**

shahverdi.senan@gmail.com · [github.com/SananShahverdi](https://github.com/SananShahverdi) · Open to remote work and relocation

## Profile

I build complete software systems: FastAPI back ends, React and build-free front ends, SQL persistence, Docker packaging, and the tests that prove they work. My portfolio contains 23 runnable projects, including 19 products served from one local hub, backed by 370 automated tests and 62 browser checks. In machine learning I care about honest evaluation: held-out data, baselines, significance tests, and results that a reviewer can reproduce.

## Skills

**Languages:** Python, TypeScript, JavaScript, SQL, HTML, CSS; working knowledge of Go, Java, C#, C, C++, and PHP
**Back end:** FastAPI, Pydantic, REST APIs, SQLAlchemy, SQLite, PostgreSQL, idempotent and transactional APIs, optimistic concurrency
**Front end:** React, Vite, TypeScript, Three.js, accessible and responsive UI, internationalization (English, Azerbaijani, Russian)
**Machine learning & data:** PyTorch, reinforcement learning (PPO, Q-learning, DQN), scikit-learn, NumPy, pandas, SciPy, time-series evaluation, GARCH, Kalman filtering, discrete-event simulation
**Quality & delivery:** pytest, Puppeteer browser tests, Docker Compose, GitHub Actions, Cloudflare Workers, Linux

## Selected projects

### Multi-Task PPO Lab · PyTorch, FastAPI, JavaScript
- Implemented Proximal Policy Optimization with GAE from scratch; one convolutional network with per-task heads learns gridworld navigation and a key-and-door task.
- On 200 unseen layouts per task, the agent solves 100% and 99.5% of episodes at 99% and 98% of optimal path length, against 91.5% and 20.5% success for a random agent.
- Diagnosed why the original prototype could not learn (off-policy updates, an invisible goal, collapsed features, a reward that punished exploration) and added tests that fail if learning regresses.

### NeuroFlow · Python, discrete-event simulation, reinforcement learning
- Built a queueing-network simulator whose single-queue results match M/M/1 and M/D/1 theory within 5% in automated tests.
- Compared shortest-path, load-aware distance-vector, and Q-routing across load: adaptive routing halves delay near saturation, and at 130% overload Q-routing is the only policy that stays usable (168 time units, against 847 for shortest paths) while load-aware distance-vector routing oscillates.

### ASP-1 · Python, NumPy, estimation and control
- Two-year mission simulator for a power-limited deep-space probe that decides for itself when to spend a wake window on a navigation fix and what to downlink.
- A 9-state Kalman filter, checked for statistical consistency with NEES over 120 runs, drives an uncertainty-triggered policy that matches the tail error of fixed-schedule navigation with 43% fewer fixes and 15% more science time (20 seeds).
- Routine telemetry is arithmetic-coded with a bigram model and anomalies are sent verbatim: 13.8× smaller than raw text, lossless, with every anomaly flagged; an eigenaxis reaction-wheel controller settled all 100 random slews, in 1.7× the bang-bang lower bound on average.

### Quant Research Lab · Python, scikit-learn, SciPy, FastAPI
- Walk-forward forecasting study on ten years of daily prices with point-in-time features, a random-walk baseline, and Diebold-Mariano tests; tests prove that features and forecasts do not change when future data changes.
- Cost-aware signal backtest against buy-and-hold, plus VaR, expected shortfall, a hand-written GARCH(1,1) maximum-likelihood fit, and Hurst exponent analysis.

### Portfolio hub and 19 products · FastAPI, React, SQLAlchemy, Docker
- One server hosts 19 independently runnable products, each with its own API, console, documentation, and tests; `npm start` loads demo data so every console opens populated.
- Products include a knowledge base that enforces access rules before retrieval and answers only with exact citations, an incident assistant that requires human approval before remediation, a WebAssembly plugin runtime with fuel, memory, and deadline limits, and a stream-analytics console with explainable risk scores.
- Wrote a shared SQLAlchemy unit-of-work adapter that persists state to SQLite or PostgreSQL; every product starts with `docker compose up`, and PostgreSQL data survives container restarts in automated checks.

### MIT OCW Smart Scraper · Python, Selenium, BeautifulSoup, PDF tooling
- Command-line archiver that discovers MIT OpenCourseWare courses and packages them into organized folders with a single merged PDF, captions, and transcripts.
- A live archive of MIT 6.0001 produced 119 sections and a 1,110-page merged PDF with a table of contents; fixed a bug that skipped every video-lecture page.

### Effekt website · React, TypeScript, Three.js
- Multilingual portfolio site for bath, sauna, and pool projects with an interactive WebGL water introduction, deployed on Cloudflare Workers.
- Added syllable-based soft hyphenation for Azerbaijani and Russian headings, which browsers cannot hyphenate, and verified heading fit at five screen widths in three languages.

## Engineering practice

- Test what matters: queueing theory for simulators, look-ahead checks for forecasting, restart checks for persistence, and real browser workflows for interfaces.
- Report results against baselines, including the ones that are unflattering.
- Keep scope honest: simulations, synthetic data, and offline providers are labeled as such.
