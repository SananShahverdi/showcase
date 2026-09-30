# Architecture

## System goal

Let someone test a price-forecasting or trading-signal idea in a way that cannot flatter it: no future data in features, out-of-sample scoring against a naive baseline, trading costs, and explicit tail risk.

## Context

```mermaid
flowchart LR
    user[Researcher] --> ui[Browser console]
    user --> cli[CLI report]
    ui -->|JSON| api[FastAPI routes]
    cli --> svc
    api --> svc[LabService<br/>datasets and cached studies]
    svc --> data[data.py<br/>CSV loading]
    svc --> feat[features.py<br/>point-in-time features]
    svc --> fc[forecasting.py<br/>walk-forward and DM test]
    svc --> st[strategy.py<br/>TTPS backtest]
    svc --> rk[risk.py<br/>VaR, GARCH, Hurst]
    files[(Bundled CSVs)] --> svc
```

## Walk-forward study

```mermaid
sequenceDiagram
    participant S as LabService
    participant F as features
    participant W as walk_forward
    S->>F: build_features(prices)
    F-->>S: X (data up to t), target (return t to t+1)
    loop every `step` rows from `min_train`
        S->>W: fit each model on rows [0, origin)
        W-->>S: predictions for rows [origin, origin + step)
    end
    S->>S: score vs random walk (RMSE, hit rate, R², DM test, long/flat economics)
```

## State

Bundled datasets load at startup. Uploads and study results are kept in process memory and cleared on restart; results are cached by their full parameter set, so repeated runs are instant and identical.

## Boundaries

Research tool only: no brokerage connection, no live data feed, no order execution. See [ADR 0001](adr/0001-core-architecture.md).
