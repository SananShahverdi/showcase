from datetime import datetime, timedelta, timezone
from real_time_fraud_risk_stream_analytics.domain.models import Event, EventType
from real_time_fraud_risk_stream_analytics.algorithms.stream_processor import StreamProcessor
from real_time_fraud_risk_stream_analytics.algorithms.scoring import ModelScoring

def test_stream_processor_velocity():
    processor = StreamProcessor()
    
    # 6 events in a row
    for i in range(6):
        e = Event(user_id="u1", type=EventType.TRANSACTION, amount=10.0, location="US", device_id="d1")
        f = processor.compute_features(e)
        if i == 5:
            assert f.velocity_1h == 6
            
def test_geo_anomaly_and_scoring():
    processor = StreamProcessor()
    
    e1 = Event(user_id="u2", type=EventType.LOGIN, amount=0.0, location="US", device_id="d1")
    processor.compute_features(e1)
    
    e2 = Event(user_id="u2", type=EventType.LOGIN, amount=0.0, location="UK", device_id="d1")
    processor.compute_features(e2)
    
    e3 = Event(user_id="u2", type=EventType.TRANSACTION, amount=5000.0, location="RU", device_id="d2")
    f3 = processor.compute_features(e3)
    
    assert f3.geo_anomaly is True
    assert f3.device_changed is True
    
    score = ModelScoring.score(e3, f3)
    assert 0.0 <= score.anomaly_score <= 1.0
    assert score.rule_score > 0.0
    assert "GEO_ANOMALY" in score.reason_codes
    assert "DEVICE_CHANGE" in score.reason_codes
    assert all(0.0 <= value <= 1.0 for value in score.contributions.values())

def test_out_of_order_event_does_not_mutate_live_state():
    processor = StreamProcessor()
    now = datetime.utcnow()
    processor.compute_features(Event(user_id="late-user", type=EventType.LOGIN, timestamp=now))
    late = processor.compute_features(Event(user_id="late-user", type=EventType.LOGIN, timestamp=now - timedelta(minutes=10)))
    assert late.is_late is True
    assert len(processor.history) == 1

def test_amount_spike_is_explainable_and_bounded():
    processor = StreamProcessor()
    processor.compute_features(Event(user_id="u3", type=EventType.TRANSACTION, amount=50, device_id="d1"))
    event = Event(user_id="u3", type=EventType.TRANSACTION, amount=20_000, location="GB", device_id="d2")
    features = processor.compute_features(event)
    score = ModelScoring.score(event, features)
    assert features.amount_spike_ratio > 100
    assert "AMOUNT_ANOMALY" in score.reason_codes
    assert 0 <= score.total_risk_score <= 1


def test_offsets_and_legacy_timestamps_share_one_event_time_window():
    processor = StreamProcessor()
    first = Event(user_id="offset-user", type=EventType.LOGIN, timestamp="2026-09-07T10:00:00")
    processor.compute_features(first)
    following = Event(user_id="offset-user", type=EventType.LOGIN, timestamp="2026-09-07T14:01:00+04:00")
    features = processor.compute_features(following)

    assert first.timestamp.tzinfo == timezone.utc
    assert following.timestamp == datetime(2026, 9, 7, 10, 1, tzinfo=timezone.utc)
    assert features.velocity_1h == 2
    assert features.is_late is False
