"""Heliocentric orbit truth model and a Kalman filter for position and velocity.

State: position r (m), velocity v (m/s), and an unmodelled constant-ish
acceleration b (m/s²) such as thermal recoil or solar pressure. The truth
integrates the same dynamics with process noise drawn from the filter's own
discrete noise model, so the filter's reported uncertainty can be checked
statistically (normalized estimation error squared, NEES).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MU_SUN = 1.32712440018e20  # m³/s²
AU = 1.495978707e11  # m
DAY = 86400.0
YEAR = 365.25 * DAY


def gravity(r: np.ndarray) -> np.ndarray:
    distance = float(np.linalg.norm(r))
    return -MU_SUN * r / distance ** 3


def gravity_gradient(r: np.ndarray) -> np.ndarray:
    distance = float(np.linalg.norm(r))
    unit = r / distance
    return MU_SUN / distance ** 3 * (3.0 * np.outer(unit, unit) - np.eye(3))


def propagate_orbit(r: np.ndarray, v: np.ndarray, b: np.ndarray, dt: float, substeps: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Velocity-Verlet integration of r̈ = g(r) + b."""
    h = dt / substeps
    for _ in range(substeps):
        a = gravity(r) + b
        v_half = v + 0.5 * h * a
        r = r + h * v_half
        v = v_half + 0.5 * h * (gravity(r) + b)
    return r, v


def transition(r: np.ndarray, dt: float) -> np.ndarray:
    """Linearised state transition for [r, v, b] over dt."""
    G = gravity_gradient(r)
    I = np.eye(3)
    F = np.eye(9)
    F[0:3, 0:3] = I + 0.5 * G * dt ** 2
    F[0:3, 3:6] = I * dt
    F[0:3, 6:9] = 0.5 * I * dt ** 2
    F[3:6, 0:3] = G * dt
    F[3:6, 6:9] = I * dt
    return F


def process_noise(dt: float, accel_psd: float, bias_psd: float) -> np.ndarray:
    """Exact discrete noise for white acceleration noise (PSD q_a) acting on v,
    and a random-walk bias (PSD q_b) integrated twice into r."""
    qa, qb = accel_psd, bias_psd
    blocks = np.array([
        [qa * dt ** 3 / 3 + qb * dt ** 5 / 20, qa * dt ** 2 / 2 + qb * dt ** 4 / 8, qb * dt ** 3 / 6],
        [qa * dt ** 2 / 2 + qb * dt ** 4 / 8, qa * dt + qb * dt ** 3 / 3, qb * dt ** 2 / 2],
        [qb * dt ** 3 / 6, qb * dt ** 2 / 2, qb * dt],
    ])
    return np.kron(blocks, np.eye(3))


@dataclass
class NavConfig:
    initial_position_au: float = 100.0
    initial_speed_m_s: float = 17_000.0  # outbound, roughly Voyager 1's speed
    initial_position_sigma_m: float = 10_000.0
    initial_velocity_sigma_m_s: float = 0.01
    bias_sigma_m_s2: float = 5e-10  # the scale of the Pioneer anomaly
    accel_psd: float = 1e-22  # m²/s³
    bias_psd: float = 1e-32  # m²/s⁵
    xnav_sigma_m: float = 5_000.0  # per axis, after one hour of pulsar photon timing


class NavigationFilter:
    def __init__(self, r: np.ndarray, v: np.ndarray, covariance: np.ndarray, config: NavConfig) -> None:
        self.x = np.concatenate([r, v, np.zeros(3)])
        self.P = covariance.copy()
        self.config = config

    @property
    def position(self) -> np.ndarray:
        return self.x[0:3]

    @property
    def velocity(self) -> np.ndarray:
        return self.x[3:6]

    def position_sigma(self) -> float:
        """Geometric-mean 1σ radius of the position error ellipsoid: det(P_rr)^(1/6)."""
        sign, logdet = np.linalg.slogdet(self.P[0:3, 0:3])
        return float(np.exp(logdet / 6.0)) if sign > 0 else 0.0

    def position_logdet(self) -> float:
        return float(np.linalg.slogdet(self.P[0:3, 0:3])[1])

    def predict(self, dt: float) -> None:
        F = transition(self.position, dt)
        r, v = propagate_orbit(self.position, self.velocity, self.x[6:9], dt)
        self.x = np.concatenate([r, v, self.x[6:9]])
        self.P = F @ self.P @ F.T + process_noise(dt, self.config.accel_psd, self.config.bias_psd)
        self.P = 0.5 * (self.P + self.P.T)

    def apply_maneuver(self, delta_v: np.ndarray, execution_sigma_m_s: float) -> None:
        """A commanded burn: the filter knows the command but not the execution error."""
        self.x[3:6] += delta_v
        self.P[3:6, 3:6] += np.eye(3) * execution_sigma_m_s ** 2

    def update_position(self, measurement: np.ndarray, sigma_m: float) -> None:
        """Position fix (e.g. X-ray pulsar navigation), Joseph-form update."""
        H = np.zeros((3, 9))
        H[:, 0:3] = np.eye(3)
        R = np.eye(3) * sigma_m ** 2
        S = H @ self.P @ H.T + R
        K = np.linalg.solve(S, H @ self.P).T
        self.x = self.x + K @ (measurement - self.position)
        A = np.eye(9) - K @ H
        self.P = A @ self.P @ A.T + K @ R @ K.T
        self.P = 0.5 * (self.P + self.P.T)

    def nees(self, true_r: np.ndarray, true_v: np.ndarray, true_b: np.ndarray) -> float:
        error = np.concatenate([true_r, true_v, true_b]) - self.x
        scale = np.sqrt(np.diag(self.P))  # the entries span ~27 orders of magnitude
        return float((error / scale) @ np.linalg.solve(self.P / np.outer(scale, scale), error / scale))


class Trajectory:
    """The true spacecraft state, including the unknown acceleration bias."""

    def __init__(self, config: NavConfig, rng: np.random.Generator) -> None:
        self.config = config
        self.rng = rng
        direction = np.array([1.0, 0.3, 0.1]) / np.linalg.norm([1.0, 0.3, 0.1])
        self.r = direction * config.initial_position_au * AU
        self.v = direction * config.initial_speed_m_s
        self.b = rng.normal(scale=config.bias_sigma_m_s2, size=3)

    def initial_covariance(self) -> np.ndarray:
        c = self.config
        return np.diag([c.initial_position_sigma_m ** 2] * 3 + [c.initial_velocity_sigma_m_s ** 2] * 3 + [c.bias_sigma_m_s2 ** 2] * 3)

    def make_filter(self) -> NavigationFilter:
        """A filter whose initial estimate is drawn from its own stated uncertainty."""
        P0 = self.initial_covariance()
        error = self.rng.multivariate_normal(np.zeros(9), P0)
        nav = NavigationFilter(self.r + error[0:3], self.v + error[3:6], P0, self.config)
        nav.x[6:9] = self.b + error[6:9]
        return nav

    def advance(self, dt: float) -> None:
        self.r, self.v = propagate_orbit(self.r, self.v, self.b, dt)
        Q = process_noise(dt, self.config.accel_psd, self.config.bias_psd)
        noise = np.linalg.cholesky(Q + np.eye(9) * 1e-40) @ self.rng.normal(size=9)
        self.r, self.v, self.b = self.r + noise[0:3], self.v + noise[3:6], self.b + noise[6:9]

    def maneuver(self, delta_v: np.ndarray, execution_sigma_m_s: float) -> None:
        self.v = self.v + delta_v + self.rng.normal(scale=execution_sigma_m_s, size=3)

    def xnav_measurement(self) -> np.ndarray:
        return self.r + self.rng.normal(scale=self.config.xnav_sigma_m, size=3)
