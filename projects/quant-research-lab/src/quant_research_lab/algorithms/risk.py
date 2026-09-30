"""Return distribution, tail risk, GARCH(1,1) volatility, and Hurst exponent."""

from __future__ import annotations

import math

import numpy as np
from scipy import optimize, stats


def value_at_risk(returns: np.ndarray, level: float = 0.95) -> dict[str, float]:
    """One-day loss thresholds, reported as positive fractions of value."""
    simple = np.expm1(returns)
    cutoff = np.quantile(simple, 1 - level)
    tail = simple[simple <= cutoff]
    mu, sigma = simple.mean(), simple.std(ddof=1)
    return {
        "historical_var": float(-cutoff),
        "historical_cvar": float(-tail.mean()),
        "gaussian_var": float(-(mu + sigma * stats.norm.ppf(1 - level))),
    }


def _garch_filter(params: np.ndarray, r: np.ndarray) -> np.ndarray:
    omega, alpha, beta = params
    variance = np.empty_like(r)
    variance[0] = r.var()
    for t in range(1, len(r)):
        variance[t] = omega + alpha * r[t - 1] ** 2 + beta * variance[t - 1]
    return variance


def fit_garch(returns: np.ndarray, horizon: int = 5) -> dict[str, float]:
    """Gaussian maximum-likelihood GARCH(1,1) on demeaned returns.

    Returns the fitted parameters and the forecast daily volatility ``horizon`` days ahead.
    """
    r = (returns - returns.mean()) * 100  # percent units keep the optimizer well scaled
    var = r.var()

    def negative_log_likelihood(params):
        omega, alpha, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 0.999:
            return 1e12
        variance = _garch_filter(params, r)
        return 0.5 * np.sum(np.log(2 * np.pi * variance) + r ** 2 / variance)

    start = np.array([var * 0.05, 0.08, 0.9])
    result = optimize.minimize(negative_log_likelihood, start, method="Nelder-Mead",
                               options={"maxiter": 4000, "xatol": 1e-8, "fatol": 1e-8})
    omega, alpha, beta = result.x
    last_variance = _garch_filter(result.x, r)[-1]
    next_variance = omega + alpha * r[-1] ** 2 + beta * last_variance
    persistence = alpha + beta
    long_run = omega / (1 - persistence)
    forecast = long_run + persistence ** (horizon - 1) * (next_variance - long_run)
    return {
        "omega": float(omega / 10_000),
        "alpha": float(alpha),
        "beta": float(beta),
        "persistence": float(persistence),
        "forecast_daily_volatility": float(math.sqrt(forecast) / 100),
        "long_run_daily_volatility": float(math.sqrt(long_run) / 100),
        "converged": bool(result.success),
    }


def hurst_exponent(returns: np.ndarray, min_chunk: int = 8) -> float:
    """Rescaled-range (R/S) estimate on returns.

    About 0.5 suggests no memory, above 0.5 persistence, below 0.5 mean reversion.
    """
    n = len(returns)
    sizes = np.unique(np.floor(np.logspace(math.log10(min_chunk), math.log10(n // 2), 12)).astype(int))
    log_size, log_rs = [], []
    for size in sizes:
        chunks = returns[: n - n % size].reshape(-1, size)
        deviations = np.cumsum(chunks - chunks.mean(axis=1, keepdims=True), axis=1)
        spread = deviations.max(axis=1) - deviations.min(axis=1)
        scale = chunks.std(axis=1)
        valid = scale > 0
        if valid.any():
            log_size.append(math.log(size))
            log_rs.append(math.log(np.mean(spread[valid] / scale[valid])))
    return float(np.polyfit(log_size, log_rs, 1)[0])


def summary(returns: np.ndarray, periods: int) -> dict:
    return {
        "observations": int(len(returns)),
        "annual_return": float(np.expm1(returns.mean() * periods)),
        "annual_volatility": float(returns.std(ddof=1) * math.sqrt(periods)),
        "skew": float(stats.skew(returns)),
        "excess_kurtosis": float(stats.kurtosis(returns)),
        "var_95": value_at_risk(returns, 0.95),
        "var_99": value_at_risk(returns, 0.99),
        "garch": fit_garch(returns),
        "hurst": hurst_exponent(returns),
    }
