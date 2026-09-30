# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

- `test_algorithms.py`: CSV formats (Nasdaq newest-first, CoinMarketCap with BOM and duplicates), rejected inputs, **features unchanged when future prices change**, next-day target alignment, RSI bounds, **walk-forward forecasts unchanged when future targets change**, Diebold-Mariano power, baseline scoring, GARCH parameter recovery on simulated data, VaR ordering, Hurst ≈ 0.5 for independent returns, next-bar positions and cost accounting, always-invested equivalence to buy and hold, maximum drawdown.

## `integration/`

- `test_api.py`: bundled dataset listing, upload → forecast → strategy → risk → report journey, caching, and explicit 404/422 errors.
