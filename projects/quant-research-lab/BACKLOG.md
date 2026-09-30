# Product roadmap

## Delivered local product

- [x] Loader for Nasdaq, CoinMarketCap, CoinGecko, and plain CSV exports with chronological ordering and duplicate handling.
- [x] Point-in-time features (returns, volatility, RSI, EMA spread, drawdown, volume z-score) with a tested no-look-ahead guarantee.
- [x] Expanding-window walk-forward study of five models against a random-walk baseline, with RMSE, hit rate, out-of-sample R², Diebold-Mariano tests, and a cost-aware long/flat check.
- [x] TTPS composite-signal backtest with next-bar entry, trading costs, and a buy-and-hold benchmark.
- [x] Risk analytics: historical and Gaussian VaR, expected shortfall, GARCH(1,1) by maximum likelihood, and a Hurst exponent.
- [x] Markdown research report, CLI, API, browser console with CSV upload, unit and integration tests.

## Research extensions

- [ ] Add purged, embargoed cross-validation for multi-day targets.
- [ ] Add block-bootstrap confidence intervals for Sharpe ratios and drawdowns.
- [ ] Add walk-forward selection of TTPS weights with a held-out final period, to measure overfitting explicitly.
- [ ] Add multi-asset datasets and portfolio-level risk (correlation, CVaR contribution).
- [ ] Persist uploaded datasets and cached studies.
