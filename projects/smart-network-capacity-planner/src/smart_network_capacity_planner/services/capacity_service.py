from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from smart_network_capacity_planner.adapters.repositories import TelemetryRepository
from smart_network_capacity_planner.algorithms.forecasting import ForecastingEngine
from smart_network_capacity_planner.algorithms.optimizer import Optimizer
from smart_network_capacity_planner.domain.models import (
    DeviceHealth,
    ForecastResult,
    IngestionSummary,
    LinkSummary,
    PortfolioOverview,
    TelemetryData,
    WeeklyCapacityReport,
    WhatIfScenario,
    utc_now,
)


class CapacityService:
    def __init__(self, repo: TelemetryRepository):
        self.repo = repo

    def ingest_telemetry(self, data: List[TelemetryData]) -> IngestionSummary:
        if not data:
            raise ValueError("telemetry batch cannot be empty")
        accepted, duplicates = self.repo.save_batch(data)
        return IngestionSummary(
            received_count=len(data),
            accepted_count=accepted,
            duplicate_count=duplicates,
            affected_links=sorted({item.link_id for item in data}),
        )

    def seed_demo(self, reset: bool = False) -> IngestionSummary:
        if reset:
            self.repo.clear()
        anchor = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        definitions = [
            ("edge-baku-01", "rtr-baku-a", 10_000.0, 6_100.0, 112.0, 8.4, 0.03, DeviceHealth.HEALTHY),
            ("core-caspian-02", "rtr-core-b", 20_000.0, 15_300.0, 158.0, 12.8, 0.15, DeviceHealth.DEGRADED),
            ("branch-ganja-03", "rtr-ganja-c", 5_000.0, 2_100.0, -8.0, 18.2, 0.02, DeviceHealth.HEALTHY),
        ]
        samples: List[TelemetryData] = []
        for link_id, device_id, capacity, base, daily_trend, latency, loss, health in definitions:
            for offset in range(30):
                # Small deterministic weekday pattern makes residual bounds meaningful.
                weekly = ((offset % 7) - 3) * capacity * 0.003
                utilization = max(0.0, base + daily_trend * offset + weekly)
                samples.append(
                    TelemetryData(
                        timestamp=anchor - timedelta(days=29 - offset),
                        link_id=link_id,
                        device_id=device_id,
                        utilization_mbps=round(utilization, 2),
                        capacity_mbps=capacity,
                        throughput_mbps=round(utilization * 0.96, 2),
                        latency_ms=latency + (offset % 4) * 0.4,
                        packet_loss_pct=loss,
                        traffic_class="aggregate",
                        device_health=health,
                    )
                )
        return self.ingest_telemetry(samples)

    def list_links(self) -> List[LinkSummary]:
        now = utc_now()
        summaries: List[LinkSummary] = []
        for link_id in self.repo.list_link_ids():
            history = self.repo.get_by_link(link_id)
            latest = history[-1]
            warnings: List[str] = []
            stale = (now - latest.timestamp).total_seconds() > 48 * 3600
            if stale:
                warnings.append("Latest telemetry is more than 48 hours old.")
            if len(history) < 7:
                warnings.append("Fewer than seven samples are available.")
            if len({sample.capacity_mbps for sample in history}) > 1:
                warnings.append("Capacity changed inside the observed history.")
            summaries.append(
                LinkSummary(
                    link_id=link_id,
                    device_id=latest.device_id,
                    latest_timestamp=latest.timestamp,
                    sample_count=len(history),
                    utilization_mbps=latest.utilization_mbps,
                    capacity_mbps=latest.capacity_mbps,
                    utilization_pct=round(latest.utilization_mbps / latest.capacity_mbps * 100, 2),
                    latency_ms=latest.latency_ms,
                    packet_loss_pct=latest.packet_loss_pct,
                    device_health=latest.device_health,
                    stale=stale,
                    data_quality_warnings=warnings,
                )
            )
        return sorted(summaries, key=lambda item: item.utilization_pct, reverse=True)

    def generate_forecast(
        self,
        link_id: str,
        capacity_override: Optional[float] = None,
        growth_multiplier: float = 1.0,
        traffic_reduction_pct: float = 0.0,
        days: int = 90,
        budget_usd: Optional[float] = None,
    ) -> ForecastResult:
        history = self.repo.get_by_link(link_id)
        if not history:
            raise ValueError("No data found for link")
        latest = history[-1]
        capacity = capacity_override if capacity_override is not None else latest.capacity_mbps
        if capacity <= 0:
            raise ValueError("capacity override must be greater than zero")
        forecast_points, diagnostics = ForecastingEngine.predict(
            history,
            days_to_forecast=days,
            growth_multiplier=growth_multiplier,
            traffic_reduction_pct=traffic_reduction_pct,
        )
        effective_current = latest.utilization_mbps * (1 - traffic_reduction_pct / 100)
        risk = ForecastingEngine.calculate_risk(
            forecast_points,
            capacity,
            link_id,
            current_utilization_mbps=effective_current,
            latency_ms=latest.latency_ms,
            packet_loss_pct=latest.packet_loss_pct,
        )
        recommendations = Optimizer.generate_recommendations(risk, capacity, budget_usd)
        return ForecastResult(
            link_id=link_id,
            capacity_mbps=capacity,
            historical_data=history,
            forecast_points=forecast_points,
            diagnostics=diagnostics,
            risk=risk,
            recommendations=recommendations,
        )

    def run_what_if(self, link_id: str, scenario: WhatIfScenario) -> WhatIfScenario:
        history = self.repo.get_by_link(link_id)
        if not history:
            raise ValueError("No data found for link")
        baseline = self.generate_forecast(link_id, days=scenario.forecast_days)
        new_capacity = history[-1].capacity_mbps + scenario.added_capacity_mbps
        result = self.generate_forecast(
            link_id,
            capacity_override=new_capacity,
            growth_multiplier=scenario.traffic_growth_multiplier,
            traffic_reduction_pct=scenario.traffic_reduction_pct,
            days=scenario.forecast_days,
            budget_usd=scenario.budget_usd,
        )
        scenario.forecast = result
        scenario.baseline_risk_level = baseline.risk.risk_level
        scenario.risk_reduction_pct = round(
            baseline.risk.saturation_probability_pct - result.risk.saturation_probability_pct,
            2,
        )
        scenario.headroom_delta_pct = round(
            result.risk.current_headroom_pct - baseline.risk.current_headroom_pct,
            2,
        )
        return self.repo.save_scenario(link_id, scenario)

    def get_overview(self) -> PortfolioOverview:
        links = self.list_links()
        critical = 0
        for link in links:
            forecast = self.generate_forecast(link.link_id, days=30)
            if forecast.risk.risk_level.value in {"HIGH", "CRITICAL"}:
                critical += 1
        return PortfolioOverview(
            link_count=len(links),
            sample_count=self.repo.sample_count(),
            stale_link_count=sum(1 for link in links if link.stale),
            critical_link_count=critical,
            links=links,
        )

    def weekly_report(self) -> WeeklyCapacityReport:
        overview = self.get_overview()
        forecasts = [self.generate_forecast(link.link_id, days=30) for link in overview.links]
        return WeeklyCapacityReport(
            assumptions=[
                "Forecasts use ordinary least-squares trend over all locally retained samples.",
                "95% bounds use residual error with a conservative floor for sparse histories.",
                "Recommendations are planning candidates and require change-control approval.",
            ],
            overview=overview,
            forecasts=forecasts,
        )

    @staticmethod
    def report_as_markdown(report: WeeklyCapacityReport) -> str:
        lines = [
            "# Weekly Network Capacity Report",
            "",
            f"Generated: {report.generated_at.isoformat()}",
            f"Links: {report.overview.link_count} | Samples: {report.overview.sample_count} | High/Critical: {report.overview.critical_link_count}",
            "",
            "## Planning assumptions",
            *[f"- {assumption}" for assumption in report.assumptions],
            "",
            "## Link outlook",
            "",
            "| Link | Utilization | Risk | Days to threshold | Trend Mbps/day |",
            "|---|---:|---|---:|---:|",
        ]
        for forecast in report.forecasts:
            current = forecast.historical_data[-1]
            days = forecast.risk.estimated_days_to_saturation or "Beyond horizon"
            lines.append(
                f"| {forecast.link_id} | {current.utilization_mbps / forecast.capacity_mbps * 100:.1f}% | "
                f"{forecast.risk.risk_level.value} | {days} | {forecast.diagnostics.slope_mbps_per_day:.1f} |"
            )
        lines.extend(["", "## Recommended actions", ""])
        for forecast in report.forecasts:
            for recommendation in forecast.recommendations:
                if recommendation.selected:
                    lines.append(
                        f"- **{forecast.link_id} — {recommendation.action}:** {recommendation.description} "
                        f"(estimated ${recommendation.cost_estimate_usd:,.0f})"
                    )
        return "\n".join(lines) + "\n"

