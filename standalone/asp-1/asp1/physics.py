"""Rigid-body attitude dynamics with a reaction-wheel assembly.

Quaternions are scalar-first (w, x, y, z) and rotate body vectors into the
inertial frame. Angular velocity is expressed in the body frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def normalize(q: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(q))
    if norm == 0.0:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / norm


def multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ])


def conjugate(q: np.ndarray) -> np.ndarray:
    return np.array([q[0], -q[1], -q[2], -q[3]])


def to_matrix(q: np.ndarray) -> np.ndarray:
    w, x, y, z = normalize(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def from_axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    return np.concatenate([[np.cos(angle / 2)], np.sin(angle / 2) * axis])


def angle_between(a: np.ndarray, b: np.ndarray) -> float:
    """Rotation angle, in radians, that takes attitude a to attitude b."""
    w = abs(float(np.dot(normalize(a), normalize(b))))
    return 2.0 * float(np.arccos(min(1.0, w)))


def derivative(q: np.ndarray, omega: np.ndarray) -> np.ndarray:
    return 0.5 * multiply(q, np.concatenate([[0.0], omega]))


class ReactionWheels:
    """Wheels along the columns of `axes`; torques and momenta are per wheel."""

    def __init__(self, axes: np.ndarray, max_torque: float, max_momentum: float) -> None:
        self.axes = np.asarray(axes, dtype=float)
        self.max_torque = float(max_torque)
        self.max_momentum = float(max_momentum)
        self.momentum = np.zeros(self.axes.shape[1])
        self._pinv = np.linalg.pinv(self.axes)

    @staticmethod
    def pyramid() -> np.ndarray:
        """Four wheels in a tetrahedral arrangement: any three span the body axes."""
        axes = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)
        return (axes / np.linalg.norm(axes, axis=1, keepdims=True)).T

    def max_body_torque(self, direction: np.ndarray) -> float:
        """Largest body torque magnitude available along a unit direction."""
        per_unit = np.abs(self._pinv @ direction).max()
        return self.max_torque / per_unit

    def wheel_torques(self, body_torque: np.ndarray) -> np.ndarray:
        """Wheel torques that produce the requested body torque, scaled down
        uniformly (keeping its direction) when a wheel would exceed its limit,
        and zeroed for any wheel already saturated in that direction."""
        torques = -(self._pinv @ body_torque)
        peak = np.abs(torques).max()
        if peak > self.max_torque:
            torques *= self.max_torque / peak
        saturated = (np.abs(self.momentum) >= self.max_momentum) & (np.sign(torques) == np.sign(self.momentum))
        torques[saturated] = 0.0
        return torques

    @property
    def body_momentum(self) -> np.ndarray:
        return self.axes @ self.momentum


@dataclass
class AttitudeState:
    q: np.ndarray
    omega: np.ndarray


class Spacecraft:
    """Attitude dynamics J·ω̇ = τ_ext − A·ḣ − ω × (J·ω + A·h), integrated with RK4."""

    def __init__(self, inertia: np.ndarray, wheels: ReactionWheels) -> None:
        self.inertia = np.asarray(inertia, dtype=float)
        self.inv_inertia = np.linalg.inv(self.inertia)
        self.wheels = wheels
        self.state = AttitudeState(np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(3))
        self.effort = 0.0  # accumulated |wheel torque| · time, N·m·s

    def reset(self, q: np.ndarray, omega: np.ndarray | None = None) -> None:
        self.state = AttitudeState(normalize(np.asarray(q, dtype=float)), np.zeros(3) if omega is None else np.asarray(omega, dtype=float))
        self.wheels.momentum[:] = 0.0
        self.effort = 0.0

    def total_momentum_inertial(self) -> np.ndarray:
        """Total angular momentum in the inertial frame; conserved without external torque."""
        body = self.inertia @ self.state.omega + self.wheels.body_momentum
        return to_matrix(self.state.q) @ body

    def step(self, body_torque_cmd: np.ndarray, dt: float, external_torque: np.ndarray | None = None) -> AttitudeState:
        wheel_torque = self.wheels.wheel_torques(np.asarray(body_torque_cmd, dtype=float))
        external = np.zeros(3) if external_torque is None else external_torque
        axes, h0 = self.wheels.axes, self.wheels.momentum.copy()

        def rates(q: np.ndarray, omega: np.ndarray, h: np.ndarray):
            wheel_body = axes @ wheel_torque
            gyroscopic = np.cross(omega, self.inertia @ omega + axes @ h)
            omega_dot = self.inv_inertia @ (external - wheel_body - gyroscopic)
            return derivative(q, omega), omega_dot, wheel_torque

        q, w = self.state.q, self.state.omega
        k1 = rates(q, w, h0)
        k2 = rates(q + 0.5 * dt * k1[0], w + 0.5 * dt * k1[1], h0 + 0.5 * dt * k1[2])
        k3 = rates(q + 0.5 * dt * k2[0], w + 0.5 * dt * k2[1], h0 + 0.5 * dt * k2[2])
        k4 = rates(q + dt * k3[0], w + dt * k3[1], h0 + dt * k3[2])
        q = q + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        w = w + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        self.wheels.momentum = np.clip(h0 + wheel_torque * dt, -self.wheels.max_momentum, self.wheels.max_momentum)
        self.state = AttitudeState(normalize(q), w)
        self.effort += float(np.abs(wheel_torque).sum() * dt)
        return self.state
