import pytest

from smart_network_capacity_planner.adapters.repositories import TelemetryConflictError, TelemetryRepository
from smart_network_capacity_planner.domain.models import TelemetryData


def sample(link_id="core", utilization=100):
    return TelemetryData(timestamp="2026-01-01T00:00:00Z", link_id=link_id,
                         utilization_mbps=utilization, capacity_mbps=1000,
                         latency_ms=2, packet_loss_pct=0)


def test_conflicting_batch_does_not_partially_update_live_or_persisted_state(tmp_path):
    state_file = str(tmp_path / "telemetry.json")
    repo = TelemetryRepository(state_file)
    repo.save_batch([sample()])
    with pytest.raises(TelemetryConflictError):
        repo.save_batch([sample("new-link"), sample(utilization=900)])
    assert repo.list_link_ids() == ["core"]
    assert repo.sample_count() == 1
    assert TelemetryRepository(state_file).sample_count() == 1


def test_batch_internal_conflicts_are_atomic_and_identical_duplicates_count_once():
    repo = TelemetryRepository(state_file="")
    with pytest.raises(TelemetryConflictError):
        repo.save_batch([sample(), sample(utilization=900)])
    assert repo.sample_count() == 0
    assert repo.save_batch([sample(), sample()]) == (1, 1)
    assert repo.sample_count() == 1
