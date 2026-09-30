from datetime import datetime, timedelta, timezone

import pytest

from autonomous_data_quality_observatory.algorithms.engines import Connectors, DriftDetector, Profiler, RulesEngine, SafeExpression
from autonomous_data_quality_observatory.domain.models import DataSource, Rule


def test_csv_connector_profiles_real_content():
    source = DataSource(
        id="orders",
        name="Orders",
        type="csv",
        config={"content": "id,amount,status\n1,10,paid\n2,,paid\n2,40,refunded\n"},
    )
    records = Connectors.fetch_data(source)
    profile = Profiler.profile(source.id, records)

    assert profile.row_count == 3
    assert {column.name for column in profile.columns} == {"id", "amount", "status"}
    amount = next(column for column in profile.columns if column.name == "amount")
    assert amount.null_count == 1
    assert amount.unique_count == 2


def test_rules_cover_schema_volume_null_uniqueness_range_freshness_and_business_expression():
    now = datetime.now(timezone.utc)
    records = [
        {"id": 1, "amount": 10, "status": "paid"},
        {"id": 2, "amount": 20, "status": "paid"},
    ]
    profile = Profiler.profile("orders", records, source_freshness_at=now - timedelta(hours=2))
    rules = [
        Rule(id="schema", source_id="orders", rule_type="schema", parameters={"columns": ["id", "amount", "status"], "types": {"amount": "number"}}),
        Rule(id="volume", source_id="orders", rule_type="volume", parameters={"min_rows": 2, "max_rows": 3}),
        Rule(id="null", source_id="orders", rule_type="null_ratio", parameters={"column": "status", "max_ratio": 0}),
        Rule(id="unique", source_id="orders", rule_type="uniqueness", parameters={"column": "id", "min_ratio": 1}),
        Rule(id="range", source_id="orders", rule_type="range", parameters={"column": "amount", "min": 0, "max": 100}),
        Rule(id="fresh", source_id="orders", rule_type="freshness", parameters={"max_age_hours": 4}),
        Rule(id="business", source_id="orders", rule_type="business_expression", parameters={"expression": "amount >= 0 and status != ''"}),
    ]
    results = RulesEngine.evaluate(profile, rules, records)

    assert len(results) == 7
    assert all(result.passed for result in results)


def test_safe_expression_rejects_calls_and_attribute_access():
    with pytest.raises(ValueError, match="unsafe"):
        SafeExpression.evaluate("__import__('os').system('id')", {})
    with pytest.raises(ValueError, match="unsafe"):
        SafeExpression.evaluate("value.__class__", {"value": 1})


def test_drift_detects_schema_volume_and_distribution_changes():
    baseline = Profiler.profile("orders", [{"id": index, "amount": 10 + index} for index in range(20)])
    current = Profiler.profile("orders", [{"id": index, "amount_usd": 500 + index * 100} for index in range(5)])
    result = DriftDetector.detect(current, baseline)

    assert result.has_drift is True
    assert {signal.drift_type for signal in result.signals} >= {"schema", "volume"}


def test_empty_profile_is_valid_evidence():
    profile = Profiler.profile("empty", [])
    assert profile.row_count == 0
    assert profile.columns == []
    assert len(profile.data_hash) == 64

