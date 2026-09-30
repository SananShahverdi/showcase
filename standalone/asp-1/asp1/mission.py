"""The mission loop: sleep, wake, decide, act, downlink.

Between windows the probe sleeps while the energy store charges, and both the
true trajectory and the onboard estimate are propagated. At each wake it
chooses whether to spend part of the window on a pulsar navigation fix
(slew to the pulsar, integrate photons, update the filter) or give the whole
window to science (slew to the target, capture frames, gate them for downlink).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from . import control, navigation, physics, power, telemetry


@dataclass
class MissionConfig:
    years: float = 2.0
    seed: int = 7
    sleep_step_s: float = 6 * 3600.0
    xnav_integration_s: float = 3600.0
    frame_interval_s: float = 20.0
    gate_threshold: float = 8.0
    anomaly_rate: float = 0.03
    maneuver_days: tuple[float, ...] = (45.0, 200.0, 380.0, 560.0)
    maneuver_delta_v_m_s: float = 1.0
    maneuver_sigma_m_s: float = 0.02  # per-axis execution error
    inertia: tuple[float, float, float] = (120.0, 100.0, 80.0)
    wheel_torque_nm: float = 0.2
    wheel_momentum_nms: float = 20.0
    slew_dt_s: float = 0.25
    simulate_slews: bool = True
    nav: navigation.NavConfig = field(default_factory=navigation.NavConfig)
    power: power.PowerConfig = field(default_factory=power.PowerConfig)


# A policy sees the filter and the number of windows since the last fix, and decides.
Policy = Callable[[navigation.NavigationFilter, int], bool]


def never(nav, since):
    return False


def every(n: int) -> Policy:
    return lambda nav, since: since + 1 >= n


def uncertainty_above(sigma_km: float) -> Policy:
    """Fix only when the geometric-mean 1σ position uncertainty exceeds the limit.
    This is the covariance log-determinant test: logdet(P_rr) > 6·ln(σ_limit)."""
    limit = 6.0 * np.log(sigma_km * 1000.0)
    return lambda nav, since: nav.position_logdet() > limit


POLICIES: dict[str, Policy] = {
    "Never": never,
    "Every 4th window": every(4),
    "Every 2nd window": every(2),
    "Every window": every(1),
    "When 1σ > 50 km": uncertainty_above(50.0),
    "When 1σ > 20 km": uncertainty_above(20.0),
}


@dataclass
class MissionReport:
    policy: str
    seed: int
    days: list[float] = field(default_factory=list)
    error_km: list[float] = field(default_factory=list)
    sigma_km: list[float] = field(default_factory=list)
    nees: list[float] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    windows: int = 0
    fixes: int = 0
    slews: int = 0
    slew_seconds: float = 0.0
    frames: int = 0
    anomalies: int = 0
    anomalies_flagged: int = 0
    false_alarms: int = 0
    gate_bits: int = 0
    raw_bits: int = 0
    lossless: bool = True
    energy_spent_j: float = 0.0

    def summary(self) -> dict:
        errors = np.array(self.error_km)
        years = self.days[-1] / 365.25 if self.days else 1.0
        return {
            "policy": self.policy,
            "seed": self.seed,
            "mean_error_km": float(errors.mean()),
            "p95_error_km": float(np.percentile(errors, 95)),
            "max_error_km": float(errors.max()),
            "fixes_per_year": self.fixes / years,
            "science_frames_per_year": self.frames / years,
            "anomalies_flagged": self.anomalies_flagged,
            "anomalies": self.anomalies,
            "false_alarms": self.false_alarms,
            "downlink_kbit_per_year": self.gate_bits / 1000.0 / years,
            "raw_kbit_per_year": self.raw_bits / 1000.0 / years,
            "mean_nees": float(np.mean(self.nees)),
            "windows": self.windows,
            "mean_slew_s": self.slew_seconds / max(self.slews, 1),
        }


class Mission:
    def __init__(self, config: MissionConfig, policy_name: str, model: telemetry.BigramModel | None = None) -> None:
        self.config = config
        self.policy_name = policy_name
        self.policy = POLICIES[policy_name]
        rng = np.random.default_rng(config.seed)
        # Separate streams, so every policy faces the same trajectory, sky, and frames.
        self.nav_rng, self.sky_rng, self.frame_rng = (np.random.default_rng(s) for s in rng.integers(0, 2**32, 3))
        self.truth = navigation.Trajectory(config.nav, self.nav_rng)
        self.nav = self.truth.make_filter()
        self.store = power.EnergyStore(config.power)
        self.model = model or telemetry.train_model(seed=config.seed + 1000)
        self.gate = telemetry.DownlinkGate(self.model, config.gate_threshold)
        self.frames = telemetry.FrameSource(self.frame_rng, config.anomaly_rate)
        inertia = np.diag(config.inertia)
        wheels = physics.ReactionWheels(physics.ReactionWheels.pyramid(), config.wheel_torque_nm, config.wheel_momentum_nms)
        self.craft = physics.Spacecraft(inertia, wheels)
        self.craft.reset(np.array([1.0, 0.0, 0.0, 0.0]))
        self.controller = control.EigenaxisController(inertia)
        self.report = MissionReport(policy_name, config.seed)
        self.time_s = 0.0
        self.maneuvers = sorted(d * navigation.DAY for d in config.maneuver_days)

    # --- helpers -------------------------------------------------------------------------

    def _log(self, kind: str, **details) -> None:
        self.report.events.append({"day": round(self.time_s / navigation.DAY, 2), "event": kind, **details})

    def _sample(self) -> None:
        self.report.days.append(self.time_s / navigation.DAY)
        self.report.error_km.append(float(np.linalg.norm(self.truth.r - self.nav.position)) / 1000.0)
        self.report.sigma_km.append(self.nav.position_sigma() / 1000.0)
        self.report.nees.append(self.nav.nees(self.truth.r, self.truth.v, self.truth.b))

    def _advance(self, seconds: float) -> None:
        """Propagate truth and estimate, applying any burn scheduled inside the interval."""
        end = self.time_s + seconds
        while self.time_s < end - 1e-6:
            step = min(self.config.sleep_step_s, end - self.time_s)
            if self.maneuvers and self.maneuvers[0] < self.time_s + step:
                step = max(self.maneuvers[0] - self.time_s, 0.0)
            if step > 0:
                self.truth.advance(step)
                self.nav.predict(step)
                self.time_s += step
            if self.maneuvers and self.maneuvers[0] <= self.time_s + 1e-6:
                self.maneuvers.pop(0)
                direction = self.sky_rng.normal(size=3)
                delta_v = direction / np.linalg.norm(direction) * self.config.maneuver_delta_v_m_s
                self.truth.maneuver(delta_v, self.config.maneuver_sigma_m_s)
                self.nav.apply_maneuver(delta_v, self.config.maneuver_sigma_m_s)
                self._log("maneuver", delta_v_m_s=self.config.maneuver_delta_v_m_s)
            if step > 0:
                self._sample()

    def _slew(self) -> float:
        target = physics.normalize(self.sky_rng.normal(size=4))
        if self.config.simulate_slews:
            result = control.slew(self.craft, self.controller, target, dt=self.config.slew_dt_s)
            seconds = result.duration_s
        else:  # fast mode for large sweeps: the controller's typical time for this angle
            seconds = 25.0 + 0.55 * np.degrees(physics.angle_between(self.craft.state.q, target))
            self.craft.reset(target)
        self.report.slews += 1
        self.report.slew_seconds += seconds
        return seconds

    # --- main loop -----------------------------------------------------------------------

    def run(self) -> MissionReport:
        end = self.config.years * navigation.YEAR
        since_fix = 0
        self._sample()
        while True:
            sleep = self.store.seconds_until_window()
            if self.time_s + sleep >= end:
                self._advance(end - self.time_s)
                break
            self.store.charge(sleep)
            self._advance(sleep)
            fixed = self._window(since_fix)
            since_fix = 0 if fixed else since_fix + 1
        self.report.energy_spent_j = self.store.spent_j
        return self.report

    def _window(self, since_fix: int) -> bool:
        cfg = self.config
        self.report.windows += 1
        remaining = cfg.power.window_s
        sigma_before = self.nav.position_sigma() / 1000.0
        fix = self.policy(self.nav, since_fix)
        self._log("wake", sigma_km=round(sigma_before, 1), decision="navigate" if fix else "science")
        if fix:
            remaining -= self._slew()
            integration = min(cfg.xnav_integration_s, remaining)
            remaining -= integration
            self._advance_awake(cfg.power.window_s - remaining)
            self.nav.update_position(self.truth.xnav_measurement(), cfg.nav.xnav_sigma_m)
            self.report.fixes += 1
        science_start = cfg.power.window_s - remaining
        remaining -= self._slew()
        captured = max(0, int(remaining // cfg.frame_interval_s))
        flagged = 0
        for frame in self.frames.frames(captured):
            packet = self.gate.encode(frame.text)
            self.report.gate_bits += packet.bits
            self.report.raw_bits += telemetry.raw_bits(frame.text)
            self.report.frames += 1
            self.report.anomalies += frame.anomalous
            self.report.anomalies_flagged += frame.anomalous and packet.flagged
            self.report.false_alarms += (not frame.anomalous) and packet.flagged
            flagged += packet.flagged
            if self.gate.decode(packet) != frame.text:
                self.report.lossless = False
        self.store.spend(cfg.power.window_s)
        self._advance_awake(cfg.power.window_s - science_start)
        if fix:
            self._log("xnav fix", sigma_km=round(self.nav.position_sigma() / 1000.0, 1), error_km=round(self.report.error_km[-1], 1))
        else:
            self._log("science", frames=captured, flagged=flagged)
        return fix

    def _advance_awake(self, seconds: float) -> None:
        if seconds > 0:
            self._advance(seconds)


def run(policy: str = "When 1σ > 20 km", **overrides) -> MissionReport:
    return Mission(MissionConfig(**overrides), policy).run()
