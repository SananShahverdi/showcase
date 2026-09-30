from collections import Counter
from typing import Dict, List, Optional
from uuid import UUID

from real_time_fraud_risk_stream_analytics.domain.models import Alert, AnalystFeedback, Event, MetricsDashboard, Score


class AlertRepository:
    def __init__(self):
        self.alerts: Dict[UUID, Alert] = {}
        self.events: Dict[UUID, Event] = {}
        self.scores: Dict[UUID, Score] = {}

    def has_event(self, event_id: UUID) -> bool:
        return event_id in self.events

    def save_event(self, event: Event, score: Score):
        self.events[event.id] = event
        self.scores[event.id] = score

    def save(self, alert: Alert):
        self.alerts[alert.id] = alert

    def get(self, alert_id: UUID) -> Optional[Alert]:
        return self.alerts.get(alert_id)

    def get_all(self, status: AnalystFeedback | None = None) -> List[Alert]:
        alerts = list(self.alerts.values())
        if status is not None:
            alerts = [alert for alert in alerts if alert.status == status]
        return sorted(alerts, key=lambda alert: (alert.score.total_risk_score, alert.created_at), reverse=True)

    def timeline(self, user_id: str) -> List[Event]:
        return sorted((event for event in self.events.values() if event.user_id == user_id), key=lambda event: event.timestamp)

    def get_metrics(self) -> MetricsDashboard:
        alerts = list(self.alerts.values())
        statuses = Counter(alert.status for alert in alerts)
        true_pos = statuses[AnalystFeedback.TRUE_POSITIVE]
        false_pos = statuses[AnalystFeedback.FALSE_POSITIVE]
        reviewed = true_pos + false_pos
        scores = list(self.scores.values())
        midpoint = len(scores) // 2
        drift = None
        if len(scores) >= 4 and midpoint:
            baseline = sum(score.total_risk_score for score in scores[:midpoint]) / midpoint
            current_count = len(scores) - midpoint
            current = sum(score.total_risk_score for score in scores[midpoint:]) / current_count
            drift = round(abs(current - baseline), 4)
        reasons = Counter(code for alert in alerts for code in alert.score.reason_codes)
        return MetricsDashboard(
            total_events=len(self.events),
            total_alerts=len(alerts),
            pending_alerts=statuses[AnalystFeedback.PENDING],
            reviewed_alerts=reviewed,
            true_positives=true_pos,
            false_positives=false_pos,
            false_positive_rate=(false_pos / reviewed) if reviewed else 0.0,
            precision=(true_pos / reviewed) if reviewed else 0.0,
            average_risk_score=(sum(score.total_risk_score for score in scores) / len(scores)) if scores else 0.0,
            drift_index=drift,
            reason_code_counts=dict(reasons),
        )
