from __future__ import annotations

from datetime import timedelta
from math import exp, sqrt
from statistics import fmean
from typing import List, Tuple

from smart_network_capacity_planner.domain.models import (
    ForecastDiagnostics,
    ForecastPoint,
    RiskLevel,
    RiskScore,
    TelemetryData,
)


class ForecastingEngine:
    """Dependency-light linear trend forecast with residual confidence bounds."""

    @staticmethod
    def predict(
        data: List[TelemetryData],
        days_to_forecast: int = 30,
        growth_multiplier: float = 1.0,
        traffic_reduction_pct: float = 0.0,
    ) -> Tuple[List[ForecastPoint], ForecastDiagnostics]:
        if not 7 <= days_to_forecast <= 90:
            raise ValueError("days_to_forecast must be between 7 and 90")
        if not data:
            raise ValueError("at least one telemetry sample is required")

        ordered = sorted(data, key=lambda item: item.timestamp)
        latest = ordered[-1]
        origin = ordered[0].timestamp
        x = [(item.timestamp - origin).total_seconds() / 86400 for item in ordered]
        y = [item.utilization_mbps for item in ordered]
        x_mean = fmean(x)
        y_mean = fmean(y)
        denominator = sum((value - x_mean) ** 2 for value in x)
        slope = (
            sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / denominator
            if denominator > 0
            else 0.0
        )
        intercept = y_mean - slope * x_mean
        fitted = [intercept + slope * value for value in x]
        mae = fmean(abs(actual - predicted) for actual, predicted in zip(y, fitted))
        residual_sigma = sqrt(
            fmean((actual - predicted) ** 2 for actual, predicted in zip(y, fitted))
        )
        # Sparse/flat series still need an honest uncertainty envelope.
        base_uncertainty = max(residual_sigma * 1.96, latest.capacity_mbps * (0.12 if len(y) < 3 else 0.03))
        adjusted_latest = latest.utilization_mbps * (1 - traffic_reduction_pct / 100)
        adjusted_slope = slope * growth_multiplier * (1 - traffic_reduction_pct / 100)
        warnings: List[str] = []
        if len(ordered) < 3:
            warnings.append("Sparse history: confidence bounds use a conservative capacity-based floor.")
        if (ordered[-1].timestamp - ordered[0].timestamp).total_seconds() < 86400:
            warnings.append("History spans less than one day; long-horizon trend confidence is limited.")
        if slope <= 0:
            warnings.append("Observed utilization trend is flat or declining.")

        points: List[ForecastPoint] = []
        for day in range(1, days_to_forecast + 1):
            predicted = max(0.0, adjusted_latest + adjusted_slope * day)
            horizon_scale = sqrt(1 + day / max(len(ordered), 1))
            uncertainty = base_uncertainty * horizon_scale
            points.append(
                ForecastPoint(
                    timestamp=latest.timestamp + timedelta(days=day),
                    predicted_mbps=round(predicted, 3),
                    lower_bound_mbps=round(max(0.0, predicted - uncertainty), 3),
                    upper_bound_mbps=round(predicted + uncertainty, 3),
                )
            )

        diagnostics = ForecastDiagnostics(
            method="ordinary-least-squares-linear-trend",
            sample_count=len(ordered),
            horizon_days=days_to_forecast,
            slope_mbps_per_day=round(adjusted_slope, 4),
            mean_absolute_error_mbps=round(mae, 4),
            warnings=warnings,
        )
        return points, diagnostics

    @staticmethod
    def calculate_risk(
        forecast: List[ForecastPoint],
        capacity_mbps: float,
        link_id: str,
        current_utilization_mbps: float | None = None,
        latency_ms: float = 0,
        packet_loss_pct: float = 0,
    ) -> RiskScore:
        if capacity_mbps <= 0:
            raise ValueError("capacity_mbps must be greater than zero")
        current = current_utilization_mbps if current_utilization_mbps is not None else 0.0
        headroom = ((capacity_mbps - current) / capacity_mbps) * 100
        crossing = next(
            (index for index, point in enumerate(forecast, start=1) if point.upper_bound_mbps >= capacity_mbps),
            None,
        )
        peak_ratio = max((point.upper_bound_mbps / capacity_mbps for point in forecast), default=current / capacity_mbps)
        # Smoothly map the worst confidence-bound ratio to 0-100% risk.
        probability = 100 / (1 + exp(-8 * (peak_ratio - 0.9)))
        if crossing is not None and crossing <= 7:
            probability = max(probability, 95)
        elif crossing is not None and crossing <= 30:
            probability = max(probability, 75)
        if packet_loss_pct >= 1:
            probability = min(100, probability + 10)

        if crossing is not None and crossing <= 7 or probability >= 90:
            level = RiskLevel.CRITICAL
        elif crossing is not None and crossing <= 30 or probability >= 70:
            level = RiskLevel.HIGH
        elif crossing is not None or probability >= 35:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        reasons = [f"Current capacity headroom is {headroom:.1f}%."]
        if crossing is None:
            reasons.append("The upper confidence bound stays below capacity in the selected horizon.")
        else:
            reasons.append(f"The upper confidence bound crosses capacity in {crossing} day(s).")
        if latency_ms >= 50:
            reasons.append(f"Latest latency is elevated at {latency_ms:.1f} ms.")
        if packet_loss_pct >= 1:
            reasons.append(f"Latest packet loss is elevated at {packet_loss_pct:.2f}%.")

        return RiskScore(
            link_id=link_id,
            saturation_probability_pct=round(min(100, probability), 2),
            estimated_days_to_saturation=crossing,
            risk_level=level,
            current_headroom_pct=round(headroom, 2),
            threshold_mbps=capacity_mbps,
            reasons=reasons,
        )
