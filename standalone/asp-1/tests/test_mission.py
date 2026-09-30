import numpy as np
import pytest

from asp1 import mission, power


def test_wake_period_follows_the_energy_budget():
    cfg = power.PowerConfig(source_w=0.2, active_w=40.0, window_s=7200.0)
    assert cfg.wake_period_s == pytest.approx(40 * 7200 / 0.2)
    store = power.EnergyStore(cfg)
    store.charge(cfg.wake_period_s - 1)
    assert not store.can_wake()
    store.charge(1)
    assert store.can_wake()
    store.spend(cfg.window_s)
    assert store.energy_j == pytest.approx(0.0, abs=1e-6)
    with pytest.raises(ValueError):
        store.spend(1.0)


@pytest.fixture(scope="module")
def reports():
    config = dict(years=1.0, seed=3, simulate_slews=False)
    return {name: mission.Mission(mission.MissionConfig(**config), name).run() for name in ("Never", "Every window", "When 1σ > 20 km")}


def test_windows_match_the_power_budget(reports):
    report = reports["Never"]
    period_days = (power.PowerConfig().wake_period_s + power.PowerConfig().window_s) / 86400
    assert report.windows == int(365.25 // period_days)
    assert report.energy_spent_j == pytest.approx(report.windows * power.PowerConfig().window_energy_j)


def test_policies_face_the_same_mission(reports):
    first = [e for e in reports["Never"].events if e["event"] == "maneuver"]
    second = [e for e in reports["Every window"].events if e["event"] == "maneuver"]
    assert [e["day"] for e in first] == [e["day"] for e in second]


def test_navigation_trades_science_for_accuracy(reports):
    never, always, triggered = (reports[k].summary() for k in ("Never", "Every window", "When 1σ > 20 km"))
    assert never["fixes_per_year"] == 0
    assert always["mean_error_km"] < triggered["mean_error_km"] < never["mean_error_km"]
    assert always["science_frames_per_year"] < triggered["science_frames_per_year"] < never["science_frames_per_year"]
    assert triggered["fixes_per_year"] < always["fixes_per_year"]


def test_every_frame_is_downlinked_losslessly(reports):
    for report in reports.values():
        assert report.lossless
        assert report.anomalies_flagged == report.anomalies
        assert report.false_alarms == 0


def test_mission_is_deterministic():
    a = mission.run("When 1σ > 50 km", years=0.3, seed=1, simulate_slews=False).summary()
    b = mission.run("When 1σ > 50 km", years=0.3, seed=1, simulate_slews=False).summary()
    assert a == b
