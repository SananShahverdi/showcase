from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from real_time_fraud_risk_stream_analytics.adapters.repositories import AlertRepository
from real_time_fraud_risk_stream_analytics.algorithms.scoring import ModelScoring
from real_time_fraud_risk_stream_analytics.algorithms.stream_processor import StreamProcessor
from real_time_fraud_risk_stream_analytics.domain.models import (
    Alert,
    AnalystFeedback,
    Event,
    EventType,
    FeedbackRequest,
    MetricsDashboard,
    ProcessingResult,
    ProcessingStatus,
)


class AnalyticsService:
    ALERT_THRESHOLD = 0.5

    def __init__(self, repo: AlertRepository):
        self.processor = StreamProcessor()
        self.repo = repo

    def reset(self) -> None:
        self.repo.alerts.clear()
        self.repo.events.clear()
        self.repo.scores.clear()
        self.processor = StreamProcessor()

    def process_event(self, event: Event) -> ProcessingResult:
        if self.repo.has_event(event.id):
            return ProcessingResult(event_id=event.id, status=ProcessingStatus.DUPLICATE, message="Event ID was already processed")

        features = self.processor.compute_features(event)
        score = ModelScoring.score(event, features)
        self.repo.save_event(event, score)
        if features.is_late:
            return ProcessingResult(event_id=event.id, status=ProcessingStatus.LATE, features=features, score=score, message="Event arrived after the five-minute live watermark and was stored without alerting")

        alert = None
        if score.total_risk_score >= self.ALERT_THRESHOLD:
            alert = Alert(event=event, features=features, score=score)
            self.repo.save(alert)
        return ProcessingResult(
            event_id=event.id,
            status=ProcessingStatus.ACCEPTED,
            features=features,
            score=score,
            alert=alert,
            message="Event scored and alert created" if alert else "Event scored below the alert threshold",
        )

    def process_batch(self, events: List[Event]) -> List[ProcessingResult]:
        return [self.process_event(event) for event in events]

    def seed_demo(self) -> List[ProcessingResult]:
        """Reset and replay a fixed synthetic event stream covering three risk patterns.

        * ``synthetic-user-100``: steady small purchases, one failed login, then a
          large purchase from a new country and device (clear fraud signal).
        * ``synthetic-user-200``: normal purchases, a burst of failed logins from a
          new device, then a payment from another country (account-takeover shape).
        * ``synthetic-user-300``: small purchases, then a moderate purchase from a
          new device and country (a borderline alert that may be a false positive).
        """
        self.reset()
        base = datetime.now(timezone.utc) - timedelta(minutes=10)

        def at(minutes: float) -> datetime:
            return base + timedelta(minutes=minutes)

        events = [
            Event(user_id="synthetic-user-100", type=EventType.TRANSACTION, amount=45 + index * 5, location="US", device_id="trusted-device", timestamp=at(index))
            for index in range(5)
        ]
        events.extend([
            Event(user_id="synthetic-user-100", type=EventType.LOGIN, location="US", device_id="trusted-device", outcome="failed", timestamp=at(5)),
            Event(user_id="synthetic-user-100", type=EventType.TRANSACTION, amount=15_000, location="CN", device_id="new-device", timestamp=at(6)),
        ])
        events.extend(
            Event(user_id="synthetic-user-200", type=EventType.TRANSACTION, amount=amount, location="GB", device_id="laptop-1", timestamp=at(index + 0.5))
            for index, amount in enumerate((30, 42, 38))
        )
        events.extend(
            Event(user_id="synthetic-user-200", type=EventType.LOGIN, location="GB", device_id="phone-9", outcome="failed", timestamp=at(index + 3.5))
            for index in range(3)
        )
        events.append(Event(user_id="synthetic-user-200", type=EventType.PAYMENT, amount=900, location="NL", device_id="phone-9", timestamp=at(7)))
        events.extend(
            Event(user_id="synthetic-user-300", type=EventType.TRANSACTION, amount=amount, location="US", device_id="tablet-3", timestamp=at(index + 0.25))
            for index, amount in enumerate((20, 25))
        )
        events.append(Event(user_id="synthetic-user-300", type=EventType.TRANSACTION, amount=150, location="CA", device_id="tablet-4", timestamp=at(8)))
        events.sort(key=lambda event: event.timestamp)
        return self.process_batch(events)

    def get_alert(self, alert_id: UUID) -> Alert:
        alert = self.repo.get(alert_id)
        if alert is None:
            raise ValueError("Alert not found")
        return alert

    def list_alerts(self, status: AnalystFeedback | None = None) -> List[Alert]:
        return self.repo.get_all(status)

    def submit_feedback(self, alert_id: UUID, request: FeedbackRequest) -> Alert:
        alert = self.get_alert(alert_id)
        if alert.version != request.expected_version:
            raise ValueError(f"Alert version conflict; current version is {alert.version}")
        if alert.status in {AnalystFeedback.TRUE_POSITIVE, AnalystFeedback.FALSE_POSITIVE}:
            raise ValueError("Final analyst decision is immutable")
        alert.status = request.feedback
        alert.reviewed_by = request.actor
        alert.review_note = request.note
        alert.reviewed_at = datetime.now(timezone.utc)
        alert.version += 1
        self.repo.save(alert)
        return alert

    def get_metrics(self) -> MetricsDashboard:
        return self.repo.get_metrics()
