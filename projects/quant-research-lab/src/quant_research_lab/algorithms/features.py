"""Point-in-time features: every value at date t uses closes and volumes up to t only."""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's relative strength index in [0, 100]."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(loss > 0, 100.0).where(gain.notna())


def zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / std.replace(0, np.nan)


def build_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Feature matrix plus ``target``: the next day's log return.

    The target is the only column that looks forward. Rows without a complete
    feature history or a next-day return are dropped.
    """
    close = prices["close"]
    ret = np.log(close).diff()
    features = pd.DataFrame(index=prices.index)
    features["ret_1"] = ret
    features["ret_5"] = np.log(close / close.shift(5))
    features["ret_20"] = np.log(close / close.shift(20))
    features["vol_20"] = ret.rolling(20).std()
    features["rsi_14"] = rsi(close) / 100
    features["ema_spread"] = ema(close, 10) / ema(close, 50) - 1
    features["drawdown_60"] = close / close.rolling(60).max() - 1
    volume = prices["volume"]
    if volume.notna().mean() > 0.9:
        features["volume_z"] = zscore(np.log(volume.where(volume > 0)), 20)
    features["target"] = ret.shift(-1)
    return features.replace([np.inf, -np.inf], np.nan).dropna()
