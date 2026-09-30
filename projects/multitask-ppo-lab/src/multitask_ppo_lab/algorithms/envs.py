"""Two procedurally generated gridworld tasks that share one observation format.

Both tasks use the same five-channel ``(C, H, W)`` observation so a single
convolutional trunk can serve both:

0. agent position
1. target (goal cell or door)
2. walls
3. key (key-door task only)
4. a constant plane set to 1 when the agent carries the key

Every layout is generated from a seed and is guaranteed solvable, so the
breadth-first-search oracle in :func:`oracle_action` always has a path.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

CHANNELS = 5
MOVES = ((-1, 0), (1, 0), (0, -1), (0, 1))  # up, down, left, right
MOVE_NAMES = ("up", "down", "left", "right")


@dataclass
class StepResult:
    observation: np.ndarray
    reward: float
    terminated: bool
    truncated: bool
    info: dict = field(default_factory=dict)


def _free_cells(walls: np.ndarray) -> list[tuple[int, int]]:
    return [tuple(cell) for cell in np.argwhere(~walls)]


def _distances(walls: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Breadth-first-search step counts from ``start``; -1 where unreachable."""
    distance = np.full(walls.shape, -1, dtype=np.int32)
    distance[start] = 0
    queue = deque([start])
    while queue:
        row, col = queue.popleft()
        for dr, dc in MOVES:
            nr, nc = row + dr, col + dc
            if 0 <= nr < walls.shape[0] and 0 <= nc < walls.shape[1] and not walls[nr, nc] and distance[nr, nc] < 0:
                distance[nr, nc] = distance[row, col] + 1
                queue.append((nr, nc))
    return distance


class GridTask:
    """Base class: a square grid with a border of walls and random interior walls."""

    name = "base"
    n_actions = 4

    def __init__(self, size: int = 7, wall_density: float = 0.15, max_steps: int | None = None, seed: int | None = None,
                 shaping: float = 0.0, gamma: float = 0.99):
        if size < 5:
            raise ValueError("size must be at least 5")
        self.size = size
        # Potential-based shaping (Ng, Harada & Russell, 1999): adding
        # ``gamma * phi(s') - phi(s)`` with phi = -shaping * remaining optimal steps
        # densifies the reward without changing which policies are optimal.
        self.shaping = shaping
        self.gamma = gamma
        self.wall_density = wall_density
        self.max_steps = max_steps or 4 * size * size
        self.rng = np.random.default_rng(seed)
        self.walls = np.zeros((size, size), dtype=bool)
        self.agent = (0, 0)
        self.steps = 0

    # -- layout -----------------------------------------------------------------
    def _random_walls(self) -> np.ndarray:
        walls = np.zeros((self.size, self.size), dtype=bool)
        walls[0, :] = walls[-1, :] = walls[:, 0] = walls[:, -1] = True
        interior = self.rng.random((self.size - 2, self.size - 2)) < self.wall_density
        walls[1:-1, 1:-1] = interior
        return walls

    def _pick(self, cells: list[tuple[int, int]], count: int) -> list[tuple[int, int]]:
        chosen = self.rng.choice(len(cells), size=count, replace=False)
        return [cells[i] for i in chosen]

    # -- stepping -----------------------------------------------------------------
    def _move(self, action: int) -> bool:
        dr, dc = MOVES[action]
        target = (self.agent[0] + dr, self.agent[1] + dc)
        if self.walls[target]:
            return False
        self.agent = target
        return True

    def observation(self) -> np.ndarray:
        raise NotImplementedError

    def reset(self) -> np.ndarray:
        raise NotImplementedError

    def step(self, action: int) -> StepResult:
        raise NotImplementedError

    def optimal_steps(self) -> int:
        raise NotImplementedError

    def _potential(self) -> float:
        return -self.shaping * self.optimal_steps()

    def _shaped(self, reward: float, before: float, terminated: bool) -> float:
        if not self.shaping:
            return reward
        after = 0.0 if terminated else self._potential()
        return reward + self.gamma * after - before


class NavigationTask(GridTask):
    """Reach the goal. Actions: up, down, left, right."""

    name = "navigation"
    n_actions = 4

    def reset(self) -> np.ndarray:
        while True:
            self.walls = self._random_walls()
            free = _free_cells(self.walls)
            if len(free) < 2:
                continue
            self.agent, self.goal = self._pick(free, 2)
            self._to_goal = _distances(self.walls, self.goal)
            if self._to_goal[self.agent] > 0:
                break
        self.steps = 0
        return self.observation()

    def observation(self) -> np.ndarray:
        obs = np.zeros((CHANNELS, self.size, self.size), dtype=np.float32)
        obs[0][self.agent] = 1
        obs[1][self.goal] = 1
        obs[2] = self.walls
        return obs

    def step(self, action: int) -> StepResult:
        if not 0 <= action < self.n_actions:
            raise ValueError(f"action must be in [0, {self.n_actions})")
        self.steps += 1
        before = self._potential() if self.shaping else 0.0
        moved = self._move(action)
        reached = self.agent == self.goal
        reward = 1.0 if reached else -0.01 - (0.0 if moved else 0.02)
        truncated = not reached and self.steps >= self.max_steps
        info = {"success": reached, "bumped": not moved, "task_reward": reward}
        return StepResult(self.observation(), self._shaped(reward, before, reached), reached, truncated, info)

    def optimal_steps(self) -> int:
        return int(self._to_goal[self.agent])


class KeyDoorTask(GridTask):
    """Pick up the key, then open the door. Actions: 4 moves, pick up, open.

    ``pick up`` works on the key's cell; ``open`` works on the door's cell while
    carrying the key. Using either at the wrong time only wastes the step: an
    extra penalty teaches an exploring agent to avoid these actions entirely,
    before it can discover that picking up the key pays off.
    """

    name = "key_door"
    n_actions = 6
    PICK_UP, OPEN = 4, 5

    def reset(self) -> np.ndarray:
        while True:
            self.walls = self._random_walls()
            free = _free_cells(self.walls)
            if len(free) < 3:
                continue
            self.agent, self.key, self.door = self._pick(free, 3)
            self._to_key = _distances(self.walls, self.key)
            self._to_door = _distances(self.walls, self.door)
            if self._to_key[self.agent] > 0 and self._to_door[self.key] > 0:
                break
        self.has_key = False
        self.steps = 0
        return self.observation()

    def observation(self) -> np.ndarray:
        obs = np.zeros((CHANNELS, self.size, self.size), dtype=np.float32)
        obs[0][self.agent] = 1
        obs[1][self.door] = 1
        obs[2] = self.walls
        if not self.has_key:
            obs[3][self.key] = 1
        obs[4] = float(self.has_key)
        return obs

    def step(self, action: int) -> StepResult:
        if not 0 <= action < self.n_actions:
            raise ValueError(f"action must be in [0, {self.n_actions})")
        self.steps += 1
        before = self._potential() if self.shaping else 0.0
        reward, opened, event = -0.01, False, None
        if action < 4:
            if not self._move(action):
                reward -= 0.02
        elif action == self.PICK_UP:
            if not self.has_key and self.agent == self.key:
                self.has_key, event = True, "picked_up"
                reward += 0.2
            # A misplaced pick-up only wastes the step (see class docstring).
        else:  # OPEN
            if self.has_key and self.agent == self.door:
                opened, event = True, "opened"
                reward = 1.0
            # A misplaced open only wastes the step.
        truncated = not opened and self.steps >= self.max_steps
        info = {"success": opened, "event": event, "task_reward": reward}
        return StepResult(self.observation(), self._shaped(reward, before, opened), opened, truncated, info)

    def optimal_steps(self) -> int:
        """Moves to the key, one pick-up, moves to the door, one open."""
        if self.has_key:
            return int(self._to_door[self.agent]) + 1
        return int(self._to_key[self.agent] + self._to_door[self.key]) + 2


TASKS = {NavigationTask.name: NavigationTask, KeyDoorTask.name: KeyDoorTask}
ACTION_NAMES = {NavigationTask.name: MOVE_NAMES, KeyDoorTask.name: MOVE_NAMES + ("pick up", "open")}


def make(task: str, **kwargs) -> GridTask:
    try:
        return TASKS[task](**kwargs)
    except KeyError:
        raise ValueError(f"Unknown task '{task}'. Choose from: {', '.join(TASKS)}") from None


def oracle_action(env: GridTask) -> int:
    """An optimal action from the current state, using breadth-first search backwards from the target."""
    if isinstance(env, KeyDoorTask):
        if not env.has_key and env.agent == env.key:
            return KeyDoorTask.PICK_UP
        if env.has_key and env.agent == env.door:
            return KeyDoorTask.OPEN
        target = env.door if env.has_key else env.key
    else:
        target = env.goal
    to_target = _distances(env.walls, target)
    here = to_target[env.agent]
    for action, (dr, dc) in enumerate(MOVES):
        cell = (env.agent[0] + dr, env.agent[1] + dc)
        if not env.walls[cell] and to_target[cell] == here - 1:
            return action
    raise RuntimeError("No path to the target; layouts are generated to be solvable")
