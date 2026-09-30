"""Dataset registry and cached research runs."""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from quant_research_lab.algorithms import data, features, forecasting, risk, strategy
from quant_research_lab.domain.models import DatasetSummary, ForecastRequest, StrategyRequest

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
BUNDLED = {
    "aapl-daily": ("Apple (AAPL) daily, 2014–2024", "Nasdaq historical-quote export", "aapl_daily_2014_2024.csv"),
    "btc-daily": ("Bitcoin (BTC-USD) daily, 2024–2025", "CoinMarketCap historical export", "btc_daily_2024_2025.csv"),
}
MAX_UPLOADS = 20
MAX_POINTS = 400


class NotFound(LookupError):
    pass


def _downsample(frame: pd.DataFrame) -> list[dict]:
    """At most ``MAX_POINTS`` evenly spaced rows for charts, always keeping the last row."""
    if len(frame) > MAX_POINTS:
        positions = np.unique(np.linspace(0, len(frame) - 1, MAX_POINTS).round().astype(int))
        frame = frame.iloc[positions]
    return [{"date": index.date().isoformat(), **{key: round(float(value), 6) for key, value in row.items()}}
            for index, row in frame.iterrows()]


def _clean(value):
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


class LabService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._datasets: dict[str, tuple[DatasetSummary, pd.DataFrame]] = {}
        self._cache: dict[tuple, dict] = {}
        for dataset_id, (name, source, filename) in BUNDLED.items():
            self._register(dataset_id, name, source, data.load_prices((DATA_DIR / filename).read_text(encoding="utf-8")), bundled=True)

    def _register(self, dataset_id: str, name: str, source: str, prices: pd.DataFrame, *, bundled: bool) -> DatasetSummary:
        summary = DatasetSummary(
            id=dataset_id, name=name, source=source, rows=len(prices),
            start=prices.index[0].date().isoformat(), end=prices.index[-1].date().isoformat(),
            periods_per_year=data.periods_per_year(prices.index),
            has_volume=bool(prices["volume"].notna().mean() > 0.9), bundled=bundled,
        )
        self._datasets[dataset_id] = (summary, prices)
        return summary

    def datasets(self) -> list[DatasetSummary]:
        return [summary for summary, _ in self._datasets.values()]

    def dataset(self, dataset_id: str) -> tuple[DatasetSummary, pd.DataFrame]:
        try:
            return self._datasets[dataset_id]
        except KeyError:
            raise NotFound(f"Dataset '{dataset_id}' does not exist.") from None

    def upload(self, name: str, csv: str) -> DatasetSummary:
        prices = data.load_prices(csv)
        digest = hashlib.sha256(csv.encode()).hexdigest()[:10]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "dataset"
        dataset_id = f"{slug}-{digest}"
        with self._lock:
            if dataset_id not in self._datasets and sum(not s.bundled for s in self.datasets()) >= MAX_UPLOADS:
                raise ValueError(f"At most {MAX_UPLOADS} uploaded datasets are kept; restart the service to clear them.")
            return self._register(dataset_id, name.strip(), "Uploaded CSV (kept in memory)", prices, bundled=False)

    def _cached(self, key: tuple, build):
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        result = _clean(build())
        with self._lock:
            self._cache[key] = result
        return result

    def forecast(self, request: ForecastRequest) -> dict:
        summary, prices = self.dataset(request.dataset_id)
        key = ("forecast", request.model_dump_json())

        def build():
            feature_frame = features.build_features(prices)
            models = list(dict.fromkeys(["random_walk", *request.models]))
            predictions = forecasting.walk_forward(feature_frame, min_train=request.min_train, step=request.step, models=models)
            scores = forecasting.score(predictions, periods=summary.periods_per_year, cost_bps=request.cost_bps)
            hold = np.expm1(predictions["actual"])
            return {
                "dataset": summary.model_dump(),
                "evaluation": {
                    "method": "expanding-window walk-forward",
                    "features": [name for name in feature_frame.columns if name != "target"],
                    "train_rows_at_first_origin": len(feature_frame) - len(predictions),
                    "test_rows": len(predictions),
                    "test_start": predictions.index[0].date().isoformat(),
                    "test_end": predictions.index[-1].date().isoformat(),
                    "retrain_every": request.step,
                    "buy_and_hold_return": float(np.prod(1 + hold) - 1),
                },
                "scores": [asdict(item) for item in scores],
            }
        return self._cached(key, build)

    def strategy(self, request: StrategyRequest) -> dict:
        summary, prices = self.dataset(request.dataset_id)
        key = ("strategy", request.model_dump_json())

        def build():
            weights = {name: getattr(request, name) for name in strategy.DEFAULT_WEIGHTS}
            result = strategy.backtest(prices, threshold=request.threshold, cost_bps=request.cost_bps,
                                       weights=weights, periods=summary.periods_per_year)
            return {
                "dataset": summary.model_dump(),
                "parameters": {"threshold": request.threshold, "cost_bps": request.cost_bps, "weights": weights},
                "strategy": asdict(result["strategy"]),
                "buy_and_hold": asdict(result["buy_and_hold"]),
                "equity": _downsample(result["equity"][["strategy", "buy_and_hold", "score"]]),
            }
        return self._cached(key, build)

    def risk(self, dataset_id: str) -> dict:
        summary, prices = self.dataset(dataset_id)

        def build():
            returns = data.log_returns(prices["close"])
            return {
                "dataset": summary.model_dump(),
                **risk.summary(returns.to_numpy(), summary.periods_per_year),
                "prices": _downsample(prices[["close"]]),
            }
        return self._cached(("risk", dataset_id), build)

    def report(self, dataset_id: str) -> str:
        summary, _ = self.dataset(dataset_id)
        fc = self.forecast(ForecastRequest(dataset_id=dataset_id))
        st = self.strategy(StrategyRequest(dataset_id=dataset_id))
        rk = self.risk(dataset_id)
        pct = lambda value: "n/a" if value is None else f"{value * 100:.2f}%"  # noqa: E731
        num = lambda value, digits=3: "n/a" if value is None else f"{value:.{digits}f}"  # noqa: E731
        ev = fc["evaluation"]
        lines = [
            f"# Research report: {summary.name}",
            "",
            f"Source: {summary.source}. {summary.rows} daily rows from {summary.start} to {summary.end}.",
            "",
            "## 1. Next-day return forecasting",
            "",
            f"{ev['method'].capitalize()} over {ev['test_rows']} out-of-sample days ({ev['test_start']} to {ev['test_end']}), retraining every {ev['retrain_every']} rows. "
            f"Buy-and-hold over the same days returned {pct(ev['buy_and_hold_return'])}.",
            "",
            "| Model | RMSE | Direction hit rate | R² vs random walk | DM p-value | Long-when-positive return | Sharpe |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in fc["scores"]:
            lines.append(f"| {row['model']} | {num(row['rmse'], 5)} | {pct(row['directional_accuracy'])} | {num(row['r2_vs_random_walk'], 4)} | "
                         f"{num(row['dm_p_value'])} | {pct(row['strategy_return'])} | {num(row['strategy_sharpe'], 2)} |")
        beaten = [row["model"] for row in fc["scores"] if row["dm_statistic"] is not None and row["dm_statistic"] < 0 and row["dm_p_value"] < 0.05]
        lines += ["", ("Models that beat the random walk at the 5% level: " + ", ".join(beaten) + ".") if beaten else
                  "No model beats the random walk at the 5% level (Diebold-Mariano test), which is the expected result for liquid markets.", ""]
        s, b = st["strategy"], st["buy_and_hold"]
        lines += [
            "## 2. TTPS signal strategy",
            "",
            f"Long when the composite score is above {st['parameters']['threshold']}, entered on the next bar, {st['parameters']['cost_bps']} bps per position change.",
            "",
            "| | Strategy | Buy and hold |",
            "|---|---:|---:|",
            f"| Total return | {pct(s['total_return'])} | {pct(b['total_return'])} |",
            f"| CAGR | {pct(s['cagr'])} | {pct(b['cagr'])} |",
            f"| Annual volatility | {pct(s['annual_volatility'])} | {pct(b['annual_volatility'])} |",
            f"| Sharpe | {num(s['sharpe'], 2)} | {num(b['sharpe'], 2)} |",
            f"| Max drawdown | {pct(s['max_drawdown'])} | {pct(b['max_drawdown'])} |",
            f"| Time in market | {pct(s['exposure'])} | 100.00% |",
            f"| Position changes | {s['trades']} | 0 |",
            "",
            "## 3. Risk",
            "",
            f"- Annualized return {pct(rk['annual_return'])}, volatility {pct(rk['annual_volatility'])}, skew {num(rk['skew'], 2)}, excess kurtosis {num(rk['excess_kurtosis'], 2)}.",
            f"- One-day 95% VaR: historical {pct(rk['var_95']['historical_var'])}, Gaussian {pct(rk['var_95']['gaussian_var'])}; expected shortfall {pct(rk['var_95']['historical_cvar'])}.",
            f"- One-day 99% VaR: historical {pct(rk['var_99']['historical_var'])}; expected shortfall {pct(rk['var_99']['historical_cvar'])}.",
            f"- GARCH(1,1): alpha {num(rk['garch']['alpha'])}, beta {num(rk['garch']['beta'])}, persistence {num(rk['garch']['persistence'])}; "
            f"5-day-ahead daily volatility {pct(rk['garch']['forecast_daily_volatility'])} vs long-run {pct(rk['garch']['long_run_daily_volatility'])}.",
            f"- Hurst exponent of returns (R/S): {num(rk['hurst'], 2)}.",
            "",
            "Past performance does not predict future results. This report is research output, not investment advice.",
            "",
        ]
        return "\n".join(lines)
