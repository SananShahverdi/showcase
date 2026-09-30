"""TTPS signal backtest: trend, tendency, pattern, and influence combined into one score.

Adapted from the original "The Architect" research script, with the corrections
that make the backtest valid: data is processed in chronological order, positions
are taken on the bar after the signal, and trading costs are charged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import ema, rsi

DEFAULT_WEIGHTS = {"trend": 0.25, "tendency": 0.25, "pattern": 0.25, "influence": 0.25}


def ttps_components(prices: pd.DataFrame) -> pd.DataFrame:
    close, volume = prices["close"], prices["volume"]
    slow = ema(close, 50)
    vol = np.log(close).diff().rolling(20).std()
    vol_mean = vol.rolling(20).mean()
    components = pd.DataFrame(index=prices.index)
    components["trend"] = (ema(close, 10) - slow) / slow
    components["tendency"] = rsi(close) / 50 - 1
    # Expanding volatility is treated as a warning, so the sign is flipped.
    components["pattern"] = -(vol - vol_mean) / vol_mean
    if volume.notna().mean() > 0.9:
        volume_mean = volume.rolling(20).mean()
        components["influence"] = ((volume - volume_mean) / volume_mean).clip(-3, 3) * np.sign(components["trend"])
    else:
        components["influence"] = 0.0
    return components


def ttps_score(prices: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    total = sum(abs(value) for value in weights.values()) or 1.0
    components = ttps_components(prices)
    return sum(components[name] * weight for name, weight in weights.items()) / total


@dataclass
class PerformanceSummary:
    total_return: float
    cagr: float
    annual_volatility: float
    sharpe: float
    max_drawdown: float
    exposure: float
    trades: int


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def summarize(daily: pd.Series, position: pd.Series, periods: int) -> PerformanceSummary:
    equity = (1 + daily).cumprod()
    years = len(daily) / periods
    total = float(equity.iloc[-1] - 1)
    std = float(daily.std(ddof=1))
    return PerformanceSummary(
        total_return=total,
        cagr=float((1 + total) ** (1 / years) - 1) if years > 0 and total > -1 else -1.0,
        annual_volatility=std * math.sqrt(periods),
        sharpe=float(daily.mean() / std * math.sqrt(periods)) if std > 0 else 0.0,
        max_drawdown=max_drawdown(equity),
        exposure=float(position.mean()),
        trades=int((position.diff().abs() > 0).sum()),
    )


def backtest(prices: pd.DataFrame, *, threshold: float = 0.0, cost_bps: float = 10.0, weights: dict[str, float] | None = None, periods: int = 252) -> dict:
    """Long when the score closes above ``threshold``, otherwise in cash.

    The position for day t+1 is decided with data up to the close of day t.
    """
    score = ttps_score(prices, weights)
    simple = prices["close"].pct_change()
    frame = pd.DataFrame({"score": score, "return": simple}).dropna()
    signal = (frame["score"] > threshold).astype(float)
    position = signal.shift(1).fillna(0.0)
    costs = position.diff().abs().fillna(position.iloc[0]) * cost_bps / 10_000
    strategy = position * frame["return"] - costs
    benchmark = frame["return"]
    return {
        "strategy": summarize(strategy, position, periods),
        "buy_and_hold": summarize(benchmark, pd.Series(1.0, index=benchmark.index), periods),
        "equity": pd.DataFrame({
            "strategy": (1 + strategy).cumprod(),
            "buy_and_hold": (1 + benchmark).cumprod(),
            "score": frame["score"],
            "position": position,
        }),
    }
