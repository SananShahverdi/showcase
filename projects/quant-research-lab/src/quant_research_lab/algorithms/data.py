"""Load daily price CSVs from common exports into one chronological frame."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

DATE_COLUMNS = ("date", "start", "snapped_at", "timestamp", "time")
CLOSE_COLUMNS = ("close", "close/last", "adj close", "adj_close", "price")
VOLUME_COLUMNS = ("volume", "total_volume")
MIN_ROWS = 60


class DataError(ValueError):
    """The input cannot be turned into a usable daily price series."""


def _number(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        series = series.astype(str).str.replace(r"[$,\s]", "", regex=True)
    return pd.to_numeric(series, errors="coerce")


def _pick(columns: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    return next((columns[name] for name in candidates if name in columns), None)


def load_prices(text: str) -> pd.DataFrame:
    """Return a frame indexed by ascending unique dates with ``close`` and ``volume``.

    Accepts Nasdaq exports (``Date, Close/Last`` with ``$`` prefixes, newest first),
    CoinMarketCap exports (``Start, End, ..., Close``), CoinGecko exports
    (``snapped_at, price, total_volume``), and plain ``Date, Close[, Volume]`` files.
    """
    try:
        raw = pd.read_csv(io.StringIO(text.lstrip("﻿")))
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataError(f"Could not parse CSV: {exc}") from exc

    columns = {str(name).strip().lower(): name for name in raw.columns}
    date_col, close_col = _pick(columns, DATE_COLUMNS), _pick(columns, CLOSE_COLUMNS)
    if not date_col or not close_col:
        raise DataError("CSV needs a date column (Date, Start, snapped_at) and a close column (Close, Close/Last, price).")
    volume_col = _pick(columns, VOLUME_COLUMNS)

    dates = pd.to_datetime(raw[date_col], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    frame = pd.DataFrame({
        "close": _number(raw[close_col]).to_numpy(),
        "volume": _number(raw[volume_col]).to_numpy() if volume_col else np.nan,
    }, index=dates)
    frame = frame[frame.index.notna() & frame["close"].notna() & (frame["close"] > 0)]
    # Exports are often newest-first; a later duplicate row wins.
    frame = frame.sort_index(kind="stable")
    frame = frame[~frame.index.duplicated(keep="last")]
    frame.index.name = "date"
    if len(frame) < MIN_ROWS:
        raise DataError(f"Need at least {MIN_ROWS} valid daily rows; found {len(frame)}.")
    return frame


def periods_per_year(index: pd.DatetimeIndex) -> int:
    """365 for markets that trade on weekends (crypto), otherwise 252."""
    weekend_share = (index.dayofweek >= 5).mean()
    return 365 if weekend_share > 0.1 else 252


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close).diff().dropna()
