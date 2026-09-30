from real_time_fraud_risk_stream_analytics.domain.models import Event, RiskFeatures, Score


class RulesEngine:
    @staticmethod
    def contributions(event: Event, features: RiskFeatures) -> dict[str, float]:
        return {
            "velocity": 0.25 if features.velocity_1h >= 6 else 0.0,
            "daily_amount": 0.35 if features.amount_sum_24h > 10_000 else 0.0,
            "failed_attempts": 0.25 if features.failed_attempts_1h >= 3 else 0.0,
            "device_change": 0.15 if features.device_changed else 0.0,
            "geo_anomaly": 0.35 if features.geo_anomaly else 0.0,
        }

    @staticmethod
    def evaluate(event: Event, features: RiskFeatures) -> float:
        return min(sum(RulesEngine.contributions(event, features).values()), 1.0)


class ModelScoring:
    """Explainable statistical scoring used when no hosted model is configured."""

    @staticmethod
    def score(event: Event, features: RiskFeatures) -> Score:
        statistical = {
            "amount_spike": min(max(features.amount_spike_ratio - 2.0, 0.0) / 8.0, 1.0) * 0.55,
            "large_amount": min(event.amount / 10_000.0, 1.0) * 0.30,
            "novel_context": (0.10 if features.device_changed else 0.0) + (0.15 if features.geo_anomaly else 0.0),
        }
        anomaly_score = min(sum(statistical.values()), 1.0)
        rule_contributions = RulesEngine.contributions(event, features)
        rule_score = min(sum(rule_contributions.values()), 1.0)
        total_risk = min((anomaly_score * 0.45) + (rule_score * 0.55), 1.0)

        reasons = []
        if statistical["amount_spike"] >= 0.2 or statistical["large_amount"] >= 0.2:
            reasons.append("AMOUNT_ANOMALY")
        if features.geo_anomaly:
            reasons.append("GEO_ANOMALY")
        if features.device_changed:
            reasons.append("DEVICE_CHANGE")
        if features.velocity_1h >= 6:
            reasons.append("HIGH_VELOCITY")
        if features.failed_attempts_1h >= 3:
            reasons.append("FAILED_ATTEMPTS")
        if anomaly_score >= 0.7:
            reasons.append("HIGH_ANOMALY_SCORE")

        contributions = {**{f"statistical.{key}": round(value, 4) for key, value in statistical.items()}, **{f"rule.{key}": value for key, value in rule_contributions.items()}}
        return Score(
            event_id=event.id,
            anomaly_score=round(anomaly_score, 4),
            rule_score=round(rule_score, 4),
            total_risk_score=round(total_risk, 4),
            reason_codes=reasons,
            contributions=contributions,
        )
