import numpy as np
import pytest

from asp1 import navigation as nav


def test_process_noise_matches_monte_carlo_of_white_acceleration():
    dt, q = 100.0, 1e-4
    rng = np.random.default_rng(0)
    steps, runs = 200, 4000
    h = dt / steps
    accel = rng.normal(scale=np.sqrt(q / h), size=(runs, steps))
    velocity = np.cumsum(accel * h, axis=1)
    position = np.cumsum(velocity * h, axis=1)
    Q = nav.process_noise(dt, q, 0.0)
    assert np.var(velocity[:, -1]) == pytest.approx(Q[3, 3], rel=0.08)
    assert np.var(position[:, -1]) == pytest.approx(Q[0, 0], rel=0.08)


def test_orbit_integrator_conserves_energy():
    r = np.array([nav.AU, 0.0, 0.0])
    v = np.array([0.0, 29_780.0, 0.0])  # roughly Earth's orbit
    energy = lambda r, v: 0.5 * v @ v - nav.MU_SUN / np.linalg.norm(r)
    start = energy(r, v)
    for _ in range(365):
        r, v = nav.propagate_orbit(r, v, np.zeros(3), nav.DAY, substeps=8)
    assert energy(r, v) == pytest.approx(start, rel=1e-6)


def test_uncertainty_grows_without_fixes_and_shrinks_with_one():
    rng = np.random.default_rng(3)
    truth = nav.Trajectory(nav.NavConfig(), rng)
    kf = truth.make_filter()
    sigma0 = kf.position_sigma()
    for _ in range(60):
        truth.advance(nav.DAY)
        kf.predict(nav.DAY)
    grown = kf.position_sigma()
    kf.update_position(truth.xnav_measurement(), kf.config.xnav_sigma_m)
    assert grown > 3 * sigma0
    assert kf.position_sigma() < kf.config.xnav_sigma_m
    assert np.all(np.linalg.eigvalsh(kf.P / np.outer(np.sqrt(np.diag(kf.P)), np.sqrt(np.diag(kf.P)))) > 0)


def test_filter_is_statistically_consistent():
    """Mean NEES over independent runs should match the state dimension (9)."""
    values = []
    for seed in range(120):
        rng = np.random.default_rng(seed)
        truth = nav.Trajectory(nav.NavConfig(), rng)
        kf = truth.make_filter()
        for day in range(90):
            truth.advance(nav.DAY)
            kf.predict(nav.DAY)
            if day == 30:
                dv = np.array([0.0, 0.5, 0.0])
                truth.maneuver(dv, 0.02)
                kf.apply_maneuver(dv, 0.02)
            if day % 20 == 19:
                kf.update_position(truth.xnav_measurement(), kf.config.xnav_sigma_m)
        values.append(kf.nees(truth.r, truth.v, truth.b))
    # chi-square(9·120)/120 has a 99% interval of roughly [7.9, 10.2]
    assert 7.9 < np.mean(values) < 10.2
