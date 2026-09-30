from __future__ import annotations

from typing import List, Optional

from smart_network_capacity_planner.domain.models import Recommendation, RiskLevel, RiskScore


class Optimizer:
    @staticmethod
    def generate_recommendations(
        risk: RiskScore,
        capacity_mbps: float = 10_000,
        budget_usd: Optional[float] = None,
    ) -> List[Recommendation]:
        if risk.risk_level == RiskLevel.LOW:
            return [
                Recommendation(
                    id=f"{risk.link_id}-monitor",
                    action="monitor",
                    description=f"Keep {risk.link_id} on the weekly planning watchlist.",
                    cost_estimate_usd=0,
                    capacity_gain_mbps=0,
                    priority=4,
                    impact="Preserves current service while the forecast remains below threshold.",
                    selection_reason="Selected because no capacity intervention is currently justified.",
                )
            ]

        upgrade_gain = max(1_000.0, round(capacity_mbps * 0.5, -2))
        upgrade_cost = round(upgrade_gain * 0.65, 2)
        upgrade_affordable = budget_usd is None or upgrade_cost <= budget_usd
        recommendations = [
            Recommendation(
                id=f"{risk.link_id}-shift",
                action="shift_traffic",
                description=f"Shift non-critical replication traffic away from {risk.link_id} during peak hours.",
                cost_estimate_usd=0,
                capacity_gain_mbps=round(capacity_mbps * 0.1, 2),
                priority=1,
                impact="Creates immediate logical headroom while preserving interactive traffic SLAs.",
                selection_reason="Selected as the fastest zero-capex mitigation.",
            ),
            Recommendation(
                id=f"{risk.link_id}-upgrade",
                action="upgrade",
                description=f"Add {upgrade_gain:,.0f} Mbps of circuit capacity to {risk.link_id}.",
                cost_estimate_usd=upgrade_cost,
                capacity_gain_mbps=upgrade_gain,
                priority=1 if risk.risk_level == RiskLevel.CRITICAL else 2,
                impact="Moves the forecast threshold and reduces congestion-driven loss and latency risk.",
                selected=upgrade_affordable,
                selection_reason=(
                    "Selected within the supplied budget."
                    if upgrade_affordable and budget_usd is not None
                    else "Selected because no budget ceiling was supplied."
                    if upgrade_affordable
                    else f"Excluded because estimated cost exceeds the ${budget_usd:,.0f} budget."
                ),
            ),
        ]
        return recommendations

