import numpy as np
import pytest

from asp1 import control, physics

INERTIA = np.diag([120.0, 100.0, 80.0])


def craft(torque=0.2, momentum=20.0):
    ship = physics.Spacecraft(INERTIA, physics.ReactionWheels(physics.ReactionWheels.pyramid(), torque, momentum))
    ship.reset(np.array([1.0, 0.0, 0.0, 0.0]))
    return ship


def test_quaternion_rotation_matches_axis_angle():
    q = physics.from_axis_angle([0, 0, 1], np.pi / 2)
    assert physics.to_matrix(q) @ np.array([1.0, 0, 0]) == pytest.approx([0, 1, 0], abs=1e-12)
    assert np.degrees(physics.angle_between(np.array([1.0, 0, 0, 0]), q)) == pytest.approx(90.0)


def test_torque_free_tumble_conserves_momentum_and_energy():
    ship = craft()
    ship.reset(np.array([1.0, 0, 0, 0]), omega=np.array([0.02, 0.05, -0.01]))
    momentum = ship.total_momentum_inertial()
    energy = 0.5 * ship.state.omega @ INERTIA @ ship.state.omega
    for _ in range(2000):
        ship.step(np.zeros(3), 0.1)
    assert ship.total_momentum_inertial() == pytest.approx(momentum, abs=1e-9)
    assert 0.5 * ship.state.omega @ INERTIA @ ship.state.omega == pytest.approx(energy, rel=1e-8)
    assert np.linalg.norm(ship.state.q) == pytest.approx(1.0)


def test_wheel_torque_is_internal_momentum_exchange():
    ship = craft()
    before = ship.total_momentum_inertial()
    for _ in range(300):
        ship.step(np.array([0.1, -0.05, 0.08]), 0.1)
    assert np.linalg.norm(ship.state.omega) > 0.01
    assert ship.total_momentum_inertial() == pytest.approx(before, abs=1e-9)


def test_wheel_limits_scale_command_and_stop_at_saturation():
    wheels = physics.ReactionWheels(physics.ReactionWheels.pyramid(), 0.2, 1.0)
    torques = wheels.wheel_torques(np.array([5.0, 0.0, 0.0]))
    assert np.abs(torques).max() == pytest.approx(0.2)
    direction = -(wheels.axes @ torques)
    assert direction / np.linalg.norm(direction) == pytest.approx([1, 0, 0], abs=1e-12)
    wheels.momentum = np.sign(torques) * 1.0  # saturated in the commanded direction
    assert np.all(wheels.wheel_torques(np.array([5.0, 0.0, 0.0])) == 0.0)


@pytest.mark.parametrize("angle", [5.0, 60.0, 120.0, 179.0])
def test_eigenaxis_slew_settles_within_twice_the_lower_bound(angle):
    ship = craft()
    target = physics.from_axis_angle([0.3, -1.0, 0.5], np.radians(angle))
    result = control.slew(ship, control.EigenaxisController(INERTIA), target, dt=0.1)
    assert result.settled
    assert result.final_error_deg < 0.05
    assert result.lower_bound_s < result.duration_s < 2.5 * result.lower_bound_s + 10
    assert result.peak_wheel_momentum < 20.0
