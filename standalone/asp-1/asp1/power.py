"""Energy-harvesting duty cycle.

A small continuous source (for example a radioisotope or betavoltaic cell)
charges an energy store. The probe sleeps until the store holds enough energy
for one working window, then wakes and spends it. The wake period follows
directly from the budget: window energy / source power.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PowerConfig:
    source_w: float = 0.2  # continuous harvest
    active_w: float = 40.0  # draw while awake (computer, sensors, radio)
    window_s: float = 7200.0  # length of one awake window

    @property
    def window_energy_j(self) -> float:
        return self.active_w * self.window_s

    @property
    def wake_period_s(self) -> float:
        """Sleep time needed to harvest one window's energy."""
        return self.window_energy_j / self.source_w

    @property
    def duty_cycle(self) -> float:
        return self.window_s / (self.window_s + self.wake_period_s)


class EnergyStore:
    """Integrates harvest and draw; reports when a full window is affordable."""

    def __init__(self, config: PowerConfig) -> None:
        self.config = config
        self.energy_j = 0.0
        self.harvested_j = 0.0
        self.spent_j = 0.0

    def charge(self, seconds: float) -> None:
        gained = self.config.source_w * seconds
        self.energy_j += gained
        self.harvested_j += gained

    def seconds_until_window(self) -> float:
        missing = max(0.0, self.config.window_energy_j - self.energy_j)
        return missing / self.config.source_w

    def can_wake(self) -> bool:
        return self.energy_j >= self.config.window_energy_j - 1e-9

    def spend(self, seconds: float, watts: float | None = None) -> float:
        """Draw power for `seconds`; the store can never go negative."""
        draw = (self.config.active_w if watts is None else watts) * seconds
        if draw > self.energy_j + 1e-9:
            raise ValueError(f"insufficient energy: need {draw:.1f} J, have {self.energy_j:.1f} J")
        self.energy_j -= draw
        self.spent_j += draw
        return draw
