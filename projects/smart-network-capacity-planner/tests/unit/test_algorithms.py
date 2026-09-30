from datetime import datetime, timedelta, timezone

from smart_network_capacity_planner.algorithms.forecasting import ForecastingEngine
from smart_network_capacity_planner.algorithms.optimizer import Optimizer
from smart_network_capacity_planner.domain.models import RiskScore, TelemetryData


def samples(start=100.0, daily_growth=10.0, capacity=500.0, count=10):
    origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        TelemetryData(
            timestamp=origin + timedelta(days=day),
            link_id="L1",
            utilization_mbps=start + day * daily_growth,
            capacity_mbps=capacity,
            latency_ms=10.0,
            packet_loss_pct=0.0,
        )
        for day in range(count)
    ]


def test_forecast_uses_observed_trend_and_reports_quality():
    forecast, diagnostics = ForecastingEngine.predict(samples(), days_to_forecast=30)

    assert len(forecast) == 30
    assert forecast[0].predicted_mbps == 200.0
    assert forecast[-1].predicted_mbps == 490.0
    assert forecast[0].lower_bound_mbps <= forecast[0].predicted_mbps <= forecast[0].upper_bound_mbps
    assert diagnostics.method == "ordinary-least-squares-linear-trend"
    assert diagnostics.sample_count == 10
    assert diagnostics.slope_mbps_per_day == 10.0
    assert diagnostics.mean_absolute_error_mbps == 0.0


def test_sparse_history_is_flat_and_has_explicit_warning():
    forecast, diagnostics = ForecastingEngine.predict(samples(count=1), days_to_forecast=7)

    assert all(point.predicted_mbps == 100 for point in forecast)
    assert any("Sparse history" in warning for warning in diagnostics.warnings)


def test_risk_calculation_critical_from_confidence_bound():
    history = samples(start=780, daily_growth=25, capacity=1_000, count=6)
    forecast, _ = ForecastingEngine.predict(history, days_to_forecast=30)
    risk = ForecastingEngine.calculate_risk(
        forecast,
        capacity_mbps=1_000,
        link_id="L1",
        current_utilization_mbps=history[-1].utilization_mbps,
    )

    assert risk.risk_level.value == "CRITICAL"
    assert risk.estimated_days_to_saturation is not None
    assert risk.estimated_days_to_saturation <= 7
    assert risk.reasons


def test_optimizer_marks_unaffordable_upgrade_but_keeps_zero_cost_mitigation():
    risk = RiskScore(
        link_id="L1",
        saturation_probability_pct=95.0,
        estimated_days_to_saturation=5,
        risk_level="CRITICAL",
        current_headroom_pct=5,
        threshold_mbps=10_000,
    )
    recommendations = Optimizer.generate_recommendations(risk, capacity_mbps=10_000, budget_usd=100)

    traffic_shift = next(item for item in recommendations if item.action == "shift_traffic")
    upgrade = next(item for item in recommendations if item.action == "upgrade")
    assert traffic_shift.selected is True
    assert upgrade.selected is False
    assert "exceeds" in upgrade.selection_reason

