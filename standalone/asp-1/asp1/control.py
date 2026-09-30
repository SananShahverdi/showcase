"""Rate-limited eigenaxis slews with reaction wheels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import physics


@dataclass
class SlewResult:
    angle_deg: float
    duration_s: float
    settled: bool
    final_error_deg: float
    peak_rate_deg_s: float
    peak_wheel_momentum: float
    effort: float
    lower_bound_s: float


class EigenaxisController:
    """Rotate about the single axis joining the current and target attitudes.

    The desired body rate points along the error axis, proportional to the
    remaining angle and capped at `max_rate`; wheel torque tracks that rate and
    cancels the gyroscopic coupling, so large slews stay on the eigenaxis
    instead of overshooting when the wheels saturate.
    """

    def __init__(self, inertia: np.ndarray, bandwidth: float = 0.6, rate_gain: float = 0.15, max_rate_deg_s: float = 3.0) -> None:
        self.inertia = np.asarray(inertia, dtype=float)
        self.bandwidth = bandwidth
        self.rate_gain = rate_gain
        self.max_rate = np.radians(max_rate_deg_s)

    def torque(self, q: np.ndarray, omega: np.ndarray, target: np.ndarray, wheel_momentum_body: np.ndarray) -> np.ndarray:
        error = physics.multiply(physics.conjugate(target), q)  # body attitude relative to the target
        if error[0] < 0:
            error = -error  # take the short way round
        angle = 2.0 * np.arctan2(np.linalg.norm(error[1:]), error[0])
        axis = error[1:] / (np.linalg.norm(error[1:]) + 1e-15)
        desired_rate = -axis * min(self.rate_gain * angle, self.max_rate)
        gyroscopic = np.cross(omega, self.inertia @ omega + wheel_momentum_body)
        return self.inertia @ (self.bandwidth * (desired_rate - omega)) + gyroscopic


def eigenaxis_lower_bound(craft: physics.Spacecraft, start: np.ndarray, target: np.ndarray) -> float:
    """Rest-to-rest bang-bang time about the eigenaxis at the wheels' full torque:
    t = 2·sqrt(θ·J_e / τ_e). No controller can slew this axis faster."""
    error = physics.multiply(physics.conjugate(start), target)
    angle = physics.angle_between(start, target)
    if angle == 0.0:
        return 0.0
    axis = error[1:] / np.linalg.norm(error[1:])
    inertia_axis = float(axis @ craft.inertia @ axis)
    torque_axis = craft.wheels.max_body_torque(axis)
    return 2.0 * float(np.sqrt(angle * inertia_axis / torque_axis))


def slew(craft: physics.Spacecraft, controller: EigenaxisController, target: np.ndarray, dt: float = 0.1,
         tolerance_deg: float = 0.05, rate_tolerance_deg_s: float = 0.01, timeout_s: float = 900.0) -> SlewResult:
    """Run the controller until the attitude settles on the target (or times out)."""
    start = craft.state.q.copy()
    effort_before = craft.effort
    bound = eigenaxis_lower_bound(craft, start, target)
    peak_rate = peak_momentum = 0.0
    elapsed = 0.0
    while elapsed < timeout_s:
        state = craft.state
        error_deg = np.degrees(physics.angle_between(state.q, target))
        if error_deg < tolerance_deg and np.degrees(np.linalg.norm(state.omega)) < rate_tolerance_deg_s:
            break
        command = controller.torque(state.q, state.omega, target, craft.wheels.body_momentum)
        craft.step(command, dt)
        elapsed += dt
        peak_rate = max(peak_rate, float(np.linalg.norm(craft.state.omega)))
        peak_momentum = max(peak_momentum, float(np.abs(craft.wheels.momentum).max()))
    final = np.degrees(physics.angle_between(craft.state.q, target))
    settled = final < tolerance_deg and np.degrees(np.linalg.norm(craft.state.omega)) < rate_tolerance_deg_s
    return SlewResult(np.degrees(physics.angle_between(start, target)), elapsed, bool(settled), float(final),
                      float(np.degrees(peak_rate)), peak_momentum, craft.effort - effort_before, bound)
