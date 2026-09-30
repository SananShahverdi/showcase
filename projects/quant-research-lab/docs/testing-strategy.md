# Testing strategy

| Layer | Location | What it proves |
|---|---|---|
| Unit | `tests/unit/test_algorithms.py` | Loader correctness, **no look-ahead in features or forecasts**, statistical tests behave on known inputs, GARCH recovers simulated parameters, backtest timing and costs are exact |
| Integration | `tests/integration/test_api.py` | Full upload-to-report journey, caching, input bounds, and explicit errors |

Leakage is tested directly rather than assumed: the feature test changes future prices, and the walk-forward test changes future targets, and both assert that earlier outputs are identical.

Tests use synthetic series with fixed seeds, so results are deterministic and fast (about 6 seconds).
