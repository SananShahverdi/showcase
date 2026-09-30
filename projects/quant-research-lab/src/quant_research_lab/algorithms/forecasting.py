"""Walk-forward next-day return forecasting scored against a random-walk baseline."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class ZeroReturn:
    """Random walk: tomorrow's expected log return is zero."""

    def fit(self, X, y):
        return self

    def predict(self, X):
        return np.zeros(len(X))


class HistoricalMean:
    """Predicts the mean return of the training window."""

    def fit(self, X, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(len(X), self.mean_)


def model_factories(seed: int = 7) -> dict:
    return {
        "random_walk": ZeroReturn,
        "historical_mean": HistoricalMean,
        "ridge": lambda: make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "random_forest": lambda: RandomForestRegressor(n_estimators=100, max_depth=4, min_samples_leaf=20, random_state=seed, n_jobs=1),
        "gradient_boosting": lambda: GradientBoostingRegressor(n_estimators=100, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=seed),
    }


@dataclass
class ModelScore:
    model: str
    rmse: float
    mae: float
    directional_accuracy: float
    r2_vs_random_walk: float
    dm_statistic: float | None
    dm_p_value: float | None
    strategy_return: float
    strategy_sharpe: float


def diebold_mariano(errors_model: np.ndarray, errors_base: np.ndarray) -> tuple[float, float] | tuple[None, None]:
    """Two-sided Diebold-Mariano test on squared-error loss for one-step forecasts.

    A negative statistic means the model's losses are lower than the baseline's.
    """
    d = errors_model ** 2 - errors_base ** 2
    if len(d) < 10 or np.allclose(d, 0):
        return None, None
    stat = d.mean() / math.sqrt(d.var(ddof=1) / len(d))
    return float(stat), float(2 * stats.norm.sf(abs(stat)))


def walk_forward(features: pd.DataFrame, *, min_train: int = 504, step: int = 63, models: list[str] | None = None, seed: int = 7) -> pd.DataFrame:
    """Out-of-sample predictions using an expanding training window.

    At origin ``i`` each model is trained on rows ``[0, i)`` and predicts rows
    ``[i, i + step)``. Row ``i - 1``'s target is the return ending on date ``i``,
    which is already known when forecasting from date ``i``, so no future data is used.
    """
    factories = model_factories(seed)
    names = models or list(factories)
    unknown = sorted(set(names) - set(factories))
    if unknown:
        raise ValueError(f"Unknown models: {', '.join(unknown)}")
    X = features.drop(columns="target").to_numpy()
    y = features["target"].to_numpy()
    n = len(features)
    min_train = max(60, min(min_train, n // 2))
    predictions = {name: np.full(n, np.nan) for name in names}
    for origin in range(min_train, n, step):
        end = min(origin + step, n)
        for name in names:
            model = factories[name]().fit(X[:origin], y[:origin])
            predictions[name][origin:end] = model.predict(X[origin:end])
    frame = pd.DataFrame(predictions, index=features.index)
    frame["actual"] = y
    return frame.iloc[min_train:]


def score(predictions: pd.DataFrame, *, periods: int = 252, cost_bps: float = 5.0) -> list[ModelScore]:
    actual = predictions["actual"].to_numpy()
    base_errors = actual - predictions["random_walk"].to_numpy() if "random_walk" in predictions else actual
    base_sse = float(np.sum(base_errors ** 2))
    results = []
    for name in predictions.columns.drop("actual"):
        predicted = predictions[name].to_numpy()
        errors = actual - predicted
        moving = actual != 0
        direction = float(np.mean(np.sign(predicted[moving]) == np.sign(actual[moving]))) if name != "random_walk" else float("nan")
        dm = diebold_mariano(errors, base_errors) if name != "random_walk" else (None, None)
        # Economic check: hold the asset for the next day only when the forecast is positive.
        position = (predicted > 0).astype(float)
        simple = np.expm1(actual)
        costs = cost_bps / 10_000 * np.abs(np.diff(np.concatenate([[0.0], position])))
        daily = position * simple - costs
        sharpe = float(daily.mean() / daily.std(ddof=1) * math.sqrt(periods)) if daily.std(ddof=1) > 0 else 0.0
        results.append(ModelScore(
            model=name,
            rmse=float(np.sqrt(np.mean(errors ** 2))),
            mae=float(np.mean(np.abs(errors))),
            directional_accuracy=direction,
            r2_vs_random_walk=float(1 - np.sum(errors ** 2) / base_sse) if base_sse > 0 else 0.0,
            dm_statistic=dm[0],
            dm_p_value=dm[1],
            strategy_return=float(np.prod(1 + daily) - 1),
            strategy_sharpe=sharpe,
        ))
    return results
