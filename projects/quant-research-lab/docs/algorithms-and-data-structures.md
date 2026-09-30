# Algorithms and data structures

## Point-in-time features

Every feature at date *t* is computed from closes and volumes up to and including *t*: 1/5/20-day log returns, 20-day volatility, Wilder RSI, 10/50 EMA spread, distance from the 60-day high, and a 20-day volume z-score. The target is the log return from *t* to *t+1*. A unit test multiplies all prices after a cutoff by three and asserts that no feature on or before the cutoff changes.

## Expanding-window walk-forward

At each origin *i* (every `step` rows after `min_train`), each model is trained on rows `[0, i)` and predicts rows `[i, i + step)`. The last training row's target is the return ending at date *i*, which is known when forecasting from *i*. Models: random walk (zero return), historical mean, ridge regression, random forest, gradient boosting.

## Scoring

- RMSE and MAE of predicted vs realized log returns.
- Directional hit rate on non-zero days.
- Out-of-sample R² against the random walk: `1 − SSE_model / SSE_random_walk`.
- Diebold-Mariano test on squared-error loss differentials, two-sided, normal approximation. A negative statistic with p < 0.05 means the model beats the baseline.
- Economic check: hold the asset for one day when the forecast is positive, net of costs, with annualized Sharpe.

## TTPS strategy

Adapted from the original "The Architect" research script. Components: trend `(EMA10 − EMA50)/EMA50`, tendency `RSI/50 − 1`, pattern `−(vol20 − mean(vol20))/mean(vol20)` (rising volatility is a warning), and influence (volume surprise signed by trend). The score is their weighted average. Position for day *t+1* = 1 if score at close *t* exceeds the threshold, else 0. Each position change costs `cost_bps`.

Corrections from the original script: rows are sorted chronologically (the export is newest-first, so the original computed indicators backwards in time), entries happen on the next bar, costs are charged, and the placeholder "PPO agent" with a zero gradient was removed rather than presented as learning.

## Risk

- Historical VaR and expected shortfall from empirical quantiles of simple returns; Gaussian VaR for comparison.
- GARCH(1,1) `σ²ₜ = ω + α r²ₜ₋₁ + β σ²ₜ₋₁` fitted by Gaussian maximum likelihood (Nelder-Mead, returns scaled to percent), with an h-step forecast that mean-reverts to `ω/(1 − α − β)`. A unit test recovers α and β from 6,000 simulated returns.
- Hurst exponent by rescaled range over log-spaced window sizes.

## Complexity

Walk-forward cost is `models × ⌈(n − min_train)/step⌉` fits. For 2,517 AAPL rows with the defaults that is 5 × 32 fits, about 20 seconds on one core, and the result is cached.
