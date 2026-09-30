import numpy as np
import pandas as pd
import pytest

from quant_research_lab.algorithms import data, features, forecasting, risk, strategy


def synthetic_prices(n=800, seed=1, weekends=False):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n, freq="D" if weekends else "B")
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n)))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"close": close, "volume": volume}, index=pd.DatetimeIndex(dates, name="date"))


# --- data loading ---------------------------------------------------------

def test_nasdaq_export_is_parsed_and_sorted_oldest_first():
    rows = [f"{d:%m/%d/%Y},${100 + i:.2f},{1000 + i},$1,$1,$1" for i, d in enumerate(pd.date_range("2024-01-01", periods=70, freq="B"))]
    text = "Date,Close/Last,Volume,Open,High,Low\n" + "\n".join(reversed(rows))
    frame = data.load_prices(text)
    assert frame.index.is_monotonic_increasing
    assert frame["close"].iloc[0] == 100 and frame["close"].iloc[-1] == 169
    assert data.periods_per_year(frame.index) == 252


def test_coinmarketcap_export_with_bom_and_duplicate_dates():
    dates = pd.date_range("2024-01-01", periods=70, freq="D")
    lines = [f"{d.date()},{d.date()},1,1,1,{50 + i},{10 + i},1" for i, d in enumerate(dates)]
    lines.append(f"{dates[-1].date()},{dates[-1].date()},1,1,1,999,1,1")
    frame = data.load_prices("﻿Start,End,Open,High,Low,Close,Volume,Market Cap\n" + "\n".join(lines))
    assert len(frame) == 70
    assert frame["close"].iloc[-1] == 999  # later duplicate wins
    assert data.periods_per_year(frame.index) == 365


@pytest.mark.parametrize("text, message", [
    ("a,b\n1,2", "date column"),
    ("Date,Close\n2024-01-01,1", "at least"),
    ("", "parse"),
])
def test_unusable_inputs_are_rejected_with_a_reason(text, message):
    with pytest.raises(data.DataError, match=message):
        data.load_prices(text)


# --- features and leakage -------------------------------------------------

def test_features_do_not_look_ahead():
    prices = synthetic_prices()
    cutoff = prices.index[500]
    changed = prices.copy()
    changed.loc[changed.index > cutoff, ["close", "volume"]] *= 3
    original = features.build_features(prices).drop(columns="target")
    shocked = features.build_features(changed).drop(columns="target")
    pd.testing.assert_frame_equal(original.loc[:cutoff], shocked.loc[:cutoff])


def test_target_is_the_next_day_log_return():
    prices = synthetic_prices()
    frame = features.build_features(prices)
    day = frame.index[10]
    following = prices.index[prices.index.get_loc(day) + 1]
    assert frame.loc[day, "target"] == pytest.approx(np.log(prices.loc[following, "close"] / prices.loc[day, "close"]))


def test_rsi_bounds_and_extremes():
    rising = pd.Series(np.arange(1, 60, dtype=float))
    assert features.rsi(rising).dropna().eq(100).all()
    values = features.rsi(synthetic_prices()["close"]).dropna()
    assert values.between(0, 100).all()


def test_walk_forward_predictions_ignore_future_targets():
    frame = features.build_features(synthetic_prices(600))
    base = forecasting.walk_forward(frame, min_train=200, step=50, models=["ridge"])
    changed = frame.copy()
    first_test = base.index[0]
    changed.loc[changed.index >= first_test + pd.Timedelta(days=120), "target"] = 0.5
    shocked = forecasting.walk_forward(changed, min_train=200, step=50, models=["ridge"])
    # Only the first block (trained on pre-test rows) is guaranteed identical.
    np.testing.assert_allclose(base["ridge"].iloc[:50], shocked["ridge"].iloc[:50])


def test_unknown_model_is_rejected():
    frame = features.build_features(synthetic_prices(300))
    with pytest.raises(ValueError, match="Unknown models"):
        forecasting.walk_forward(frame, models=["oracle"])


def test_diebold_mariano_detects_a_clearly_better_model():
    rng = np.random.default_rng(3)
    base = rng.normal(0, 1, 500)
    stat, p = forecasting.diebold_mariano(base * 0.5, base)
    assert stat < 0 and p < 0.001
    assert forecasting.diebold_mariano(base, base) == (None, None)


def test_scores_include_baseline_and_economic_results():
    frame = features.build_features(synthetic_prices(500))
    predictions = forecasting.walk_forward(frame, min_train=200, step=100, models=["random_walk", "historical_mean"])
    scores = {s.model: s for s in forecasting.score(predictions)}
    assert scores["random_walk"].r2_vs_random_walk == 0
    assert scores["random_walk"].strategy_return == 0
    assert 0 <= scores["historical_mean"].directional_accuracy <= 1


# --- risk ---------------------------------------------------------------------

def simulate_garch(n, omega, alpha, beta, seed=5):
    rng = np.random.default_rng(seed)
    r, var = np.empty(n), omega / (1 - alpha - beta)
    for t in range(n):
        r[t] = rng.normal() * np.sqrt(var)
        var = omega + alpha * r[t] ** 2 + beta * var
    return r


def test_garch_recovers_simulated_parameters():
    fit = risk.fit_garch(simulate_garch(6000, 2e-6, 0.08, 0.9))
    assert fit["converged"]
    assert fit["alpha"] == pytest.approx(0.08, abs=0.03)
    assert fit["beta"] == pytest.approx(0.9, abs=0.04)
    assert fit["forecast_daily_volatility"] > 0


def test_value_at_risk_is_ordered_and_positive():
    returns = np.random.default_rng(2).standard_t(4, 3000) * 0.01
    v95, v99 = risk.value_at_risk(returns, 0.95), risk.value_at_risk(returns, 0.99)
    assert 0 < v95["historical_var"] < v95["historical_cvar"]
    assert v95["historical_var"] < v99["historical_var"]


def test_hurst_is_near_half_for_independent_returns():
    assert risk.hurst_exponent(np.random.default_rng(4).normal(size=4000)) == pytest.approx(0.5, abs=0.1)


# --- strategy -----------------------------------------------------------------

def test_positions_trade_on_the_next_bar_and_costs_are_charged():
    prices = synthetic_prices(300)
    result = strategy.backtest(prices, cost_bps=0)
    equity = result["equity"]
    score = strategy.ttps_score(prices).loc[equity.index]
    assert (equity["position"].iloc[1:].to_numpy() == (score > 0).astype(float).iloc[:-1].to_numpy()).all()
    costly = strategy.backtest(prices, cost_bps=50)
    assert costly["strategy"].total_return < result["strategy"].total_return
    assert costly["strategy"].trades == result["strategy"].trades


def test_always_invested_signal_matches_buy_and_hold_after_entry():
    prices = synthetic_prices(300)
    result = strategy.backtest(prices, threshold=-10, cost_bps=0)
    equity = result["equity"]
    # Entry happens one bar after the first signal, so compare growth from that bar on.
    growth_strategy = equity["strategy"].iloc[-1] / equity["strategy"].iloc[0]
    growth_hold = equity["buy_and_hold"].iloc[-1] / equity["buy_and_hold"].iloc[0]
    assert growth_strategy == pytest.approx(growth_hold)
    assert result["strategy"].exposure < 1


def test_max_drawdown():
    assert strategy.max_drawdown(pd.Series([1.0, 2.0, 1.0, 3.0])) == pytest.approx(-0.5)
