from datetime import datetime, timedelta
from typing import List

from real_time_fraud_risk_stream_analytics.domain.models import Event, RiskFeatures


class StreamProcessor:
    """Event-time feature processor with bounded 24-hour local state."""

    ALLOWED_LATENESS = timedelta(minutes=5)

    def __init__(self):
        self.history: List[Event] = []
        self.watermark: datetime | None = None

    def compute_features(self, event: Event) -> RiskFeatures:
        now = event.timestamp
        is_late = self.watermark is not None and now < self.watermark - self.ALLOWED_LATENESS
        self.watermark = max(self.watermark, now) if self.watermark else now

        one_hour_ago = now - timedelta(hours=1)
        twenty_four_hours_ago = now - timedelta(hours=24)
        user_events = [
            prior for prior in self.history
            if prior.user_id == event.user_id and twenty_four_hours_ago <= prior.timestamp <= now
        ]
        hour_events = [prior for prior in user_events if prior.timestamp >= one_hour_ago]
        transaction_amounts = [prior.amount for prior in user_events if prior.amount > 0]
        baseline_amount = (sum(transaction_amounts) / len(transaction_amounts)) if transaction_amounts else max(event.amount, 1.0)
        amount_spike_ratio = event.amount / max(baseline_amount, 1.0) if event.amount > 0 else 1.0

        locations = {prior.location for prior in user_events}
        locations.add(event.location)
        devices = {prior.device_id for prior in user_events}
        devices.add(event.device_id)
        last_event = max(user_events, key=lambda item: item.timestamp) if user_events else None

        # Late events are retained for audit/replay but do not mutate live feature state.
        if not is_late:
            self.history.append(event)
            cutoff = self.watermark - timedelta(hours=24)
            self.history = [item for item in self.history if item.timestamp >= cutoff]

        return RiskFeatures(
            velocity_1h=len(hour_events) + 1,
            amount_sum_24h=sum(prior.amount for prior in user_events) + event.amount,
            distinct_locations_24h=len(locations),
            distinct_devices_24h=len(devices),
            failed_attempts_1h=sum(prior.outcome == "failed" for prior in hour_events) + (event.outcome == "failed"),
            amount_spike_ratio=round(amount_spike_ratio, 3),
            geo_anomaly=bool(user_events) and len(locations) > 1,
            device_changed=last_event is not None and last_event.device_id != event.device_id,
            history_events=len(user_events),
            is_late=is_late,
        )
