"""Loads the trained agent and serves learning curves, evaluation, and replayable episodes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from multitask_ppo_lab.algorithms.envs import ACTION_NAMES, TASKS
from multitask_ppo_lab.algorithms.envs import oracle_action
from multitask_ppo_lab.algorithms.evaluation import EVAL_SEED_OFFSET, policy_action, run_episode
from multitask_ppo_lab.algorithms.network import MultiTaskActorCritic

ARTIFACTS = Path(__file__).resolve().parents[3] / "artifacts"


class NotReady(RuntimeError):
    """No trained checkpoint is available yet."""


def frame_to_rows(observation: np.ndarray) -> dict:
    """Compact text rendering: ``#`` wall, ``A`` agent, ``G`` goal or door, ``K`` key, ``.`` floor."""
    agent, target, walls, key, carrying = observation
    rows = []
    for r in range(walls.shape[0]):
        row = []
        for c in range(walls.shape[1]):
            row.append("#" if walls[r, c] else "A" if agent[r, c] else "K" if key[r, c] else "G" if target[r, c] else ".")
        rows.append("".join(row))
    return {"rows": rows, "has_key": bool(carrying.max() > 0)}


class LabService:
    def __init__(self, artifacts: Path = ARTIFACTS) -> None:
        self.artifacts = artifacts
        self.model: MultiTaskActorCritic | None = None
        self.training: dict = {}
        path = artifacts / "policy.pt"
        if path.exists():
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
            self.model = MultiTaskActorCritic(**checkpoint["model"])
            self.model.load_state_dict(checkpoint["state_dict"])
            self.model.eval()
            self.training = checkpoint["training"]

    @property
    def ready(self) -> bool:
        return self.model is not None

    def _require(self) -> MultiTaskActorCritic:
        if self.model is None:
            raise NotReady("No trained policy found. Run: python -m multitask_ppo_lab.cli train --out artifacts")
        return self.model

    def summary(self) -> dict:
        self._require()
        history = json.loads((self.artifacts / "history.json").read_text()) if (self.artifacts / "history.json").exists() else []
        evaluation = json.loads((self.artifacts / "evaluation.json").read_text()) if (self.artifacts / "evaluation.json").exists() else []
        curves = {task: [{"update": h["update"], "env_steps": h["env_steps"], "success_rate": h["per_task"][task]["success_rate"],
                          "mean_return": h["per_task"][task]["mean_return"], "entropy": h["per_task"][task]["entropy"]}
                         for h in history] for task in self.model.tasks}
        return {
            "training": self.training,
            "parameters": sum(p.numel() for p in self.model.parameters()),
            "tasks": {task: {"actions": list(ACTION_NAMES[task])} for task in self.model.tasks},
            "curves": curves,
            "evaluation": evaluation,
            "training_seconds": history[-1]["seconds"] if history else None,
            "env_steps": history[-1]["env_steps"] if history else None,
        }

    def episode(self, task: str, policy: str, seed: int) -> dict:
        model = self._require()
        if task not in TASKS or task not in model.tasks:
            raise ValueError(f"Unknown task '{task}'")
        rng = np.random.default_rng(seed)
        choosers = {
            "ppo": lambda env, obs: policy_action(model, task, obs, greedy=False, rng=rng),
            "ppo_greedy": lambda env, obs: policy_action(model, task, obs, greedy=True),
            "random": lambda env, obs: int(rng.integers(env.n_actions)),
            "oracle": lambda env, obs: oracle_action(env),
        }
        if policy not in choosers:
            raise ValueError(f"Unknown policy '{policy}'")
        # Offset into the held-out range so the console never replays a training layout.
        run = run_episode(task, self.training["size"], EVAL_SEED_OFFSET + seed, choosers[policy])
        names = ACTION_NAMES[task]
        return {
            "task": task, "policy": policy, "seed": seed,
            "success": run["success"], "steps": run["steps"], "optimal_steps": run["optimal_steps"],
            "return": round(run["return"], 4),
            "actions": [names[a] for a in run["actions"]],
            "frames": [frame_to_rows(frame) for frame in run["frames"]],
        }
