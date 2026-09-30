from datetime import datetime, timezone
from process_mining_workflow_automation_analyzer.domain.models import Event
from process_mining_workflow_automation_analyzer.algorithms.engine import ProcessEngine

def test_process_engine():
    t1 = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc) # 5 mins
    t3 = datetime(2023, 1, 3, 10, 5, 0, tzinfo=timezone.utc) # 48 hours later (bottleneck)
    t4 = datetime(2023, 1, 3, 10, 10, 0, tzinfo=timezone.utc) # rework loop (Review again)
    
    events = [
        Event(case_id="1", activity="Start", timestamp=t1),
        Event(case_id="1", activity="Review", timestamp=t2),
        Event(case_id="1", activity="Approve", timestamp=t3),
        Event(case_id="1", activity="Review", timestamp=t4)
    ]
    
    variants, transitions, bottlenecks, rework_loops = ProcessEngine.discover(events)
    
    assert len(variants) == 1
    assert variants[0].activities_sequence == ["Start", "Review", "Approve", "Review"]
    
    assert len(transitions) == 3
    assert len(bottlenecks) == 1
    assert bottlenecks[0].source == "Review"
    assert bottlenecks[0].target == "Approve"
    
    assert "Review" in rework_loops
    assert bottlenecks[0].median_duration_seconds == 172800
    assert bottlenecks[0].p95_duration_seconds == 172800


def test_case_sla_resource_and_variant_metrics():
    events = [
        Event(case_id="1", activity="Start", timestamp="2026-01-01T00:00:00Z", resource="intake"),
        Event(case_id="1", activity="Finish", timestamp="2026-01-01T02:00:00Z", resource="ops"),
        Event(case_id="2", activity="Start", timestamp="2026-01-01T00:00:00Z", resource="intake"),
    ]
    analysis = ProcessEngine.analyze(events)
    assert analysis["variants"][0].coverage == 0.5
    assert len(analysis["sla_breaches"]) == 0
    assert analysis["resources"][0].resource == "intake"
    assert analysis["resources"][0].case_count == 2


def test_threshold_labels_are_readable():
    from process_mining_workflow_automation_analyzer.algorithms.ai_assistant import describe_duration

    assert describe_duration(86_400) == "24-hour"
    assert describe_duration(5_400) == "1.5-hour"
    assert describe_duration(1_800) == "30-minute"
    assert describe_duration(45) == "45-second"
