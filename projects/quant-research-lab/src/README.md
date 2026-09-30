# Source layout

The application lives in the `quant_research_lab` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

| Module | Contents |
|---|---|
| `models.py` | Pydantic request and response contracts with bounded parameters |

## `algorithms/`

Pure functions on pandas and NumPy data. No HTTP or state.

| Module | Contents |
|---|---|
| `data.py` | CSV format detection, cleaning, chronological ordering, trading-days-per-year detection |
| `features.py` | Point-in-time features and the next-day return target |
| `forecasting.py` | Model zoo, expanding-window walk-forward, scoring, Diebold-Mariano test |
| `strategy.py` | TTPS components and score, next-bar backtest, performance summary |
| `risk.py` | VaR and expected shortfall, GARCH(1,1) maximum likelihood, Hurst R/S |

## `services/`

| Module | Contents |
|---|---|
| `lab_service.py` | Dataset registry (bundled plus in-memory uploads), cached studies, Markdown report |

## `api/` and CLI

| Module | Contents |
|---|---|
| `api/app.py` | FastAPI factory, routes, and static console mounting |
| `cli.py` | `python -m quant_research_lab.cli <dataset-id or CSV>` prints or writes the report |
