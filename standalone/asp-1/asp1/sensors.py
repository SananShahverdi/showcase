from dataclasses import dataclass
from typing import Optional

import numpy as np

from .physics import normalize_quat, quat_from_small_angle, quat_multiply, quat_to_matrix


@dataclass
class SensorSample:
    value: np.ndarray
    sigma: float


class Gyro:
    def __init__(
        self,
        bias_rw_rad_s: float,
        noise_std_rad_s: float,
        rng: np.random.Generator,
    ) -> None:
        self.bias_rw_rad_s = float(bias_rw_rad_s)
        self.noise_std_rad_s = float(noise_std_rad_s)
        self.bias = np.zeros(3, dtype=float)
        self.rng = rng

    def sample(self, omega_true: np.ndarray, dt: float) -> SensorSample:
        self.bias += self.bias_rw_rad_s * np.sqrt(dt) * self.rng.normal(size=3)
        noise = self.noise_std_rad_s * self.rng.normal(size=3)
        return SensorSample(omega_true + self.bias + noise, self.noise_std_rad_s)


class StarTracker:
    def __init__(
        self,
        noise_std_rad: float,
        sun_blind_deg: float,
        boresight_body: np.ndarray,
        rng: np.random.Generator,
    ) -> None:
        self.noise_std_rad = float(noise_std_rad)
        self.sun_blind_deg = float(sun_blind_deg)
        self.boresight_body = boresight_body.astype(float)
        self.rng = rng

    def _is_blind(self, quat_wxyz: np.ndarray, position_m: np.ndarray) -> bool:
        sun_vec_inertial = -position_m
        norm = float(np.linalg.norm(sun_vec_inertial))
        if norm == 0.0:
            return False
        sun_unit = sun_vec_inertial / norm
        rot = quat_to_matrix(quat_wxyz)
        sun_body = rot.T @ sun_unit
        cos_angle = float(np.dot(sun_body, self.boresight_body) / np.linalg.norm(self.boresight_body))
        cos_angle = float(np.clip(cos_angle, -1.0, 1.0))
        angle_deg = float(np.degrees(np.arccos(cos_angle)))
        return angle_deg <= self.sun_blind_deg

    def sample(
        self, quat_true: np.ndarray, position_m: np.ndarray
    ) -> Optional[SensorSample]:
        if self._is_blind(quat_true, position_m):
            return None
        noise = self.noise_std_rad * self.rng.normal(size=3)
        delta_quat = quat_from_small_angle(noise)
        measured = normalize_quat(quat_multiply(quat_true, delta_quat))
        return SensorSample(measured, self.noise_std_rad)


class XNav:
    def __init__(
        self,
        noise_std_m: float,
        update_rate_hz: float,
        rng: np.random.Generator,
    ) -> None:
        self.noise_std_m = float(noise_std_m)
        self.update_period_s = 1.0 / float(update_rate_hz)
        self.rng = rng
        self._time_since = 0.0

    def step_time(self, dt: float) -> None:
        self._time_since += dt

    def sample(
        self, position_true: np.ndarray, active: bool
    ) -> Optional[SensorSample]:
        if not active or self._time_since < self.update_period_s:
            return None
        self._time_since -= self.update_period_s
        noise = self.noise_std_m * self.rng.normal(size=3)
        return SensorSample(position_true + noise, self.noise_std_m)
