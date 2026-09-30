"""Score a policy on held-out layouts against random and optimal (BFS) baselines."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import torch

from .envs import make, oracle_action
from .network import MultiTaskActorCritic

EVAL_SEED_OFFSET = 1_000_000  # evaluation layouts never overlap the training seeds
POLICIES = ("random", "ppo_sampled", "ppo_greedy", "oracle")


@dataclass
class EvalResult:
    policy: str
    task: str
    episodes: int
    success_rate: float
    mean_return: float
    mean_steps: float
    optimality: float | None  # mean of optimal_steps / steps_taken over successful episodes


def policy_action(model: MultiTaskActorCritic, task: str, observation: np.ndarray, greedy: bool = True, rng=None) -> int:
    with torch.no_grad():
        logits, _ = model(torch.from_numpy(observation).unsqueeze(0), task)
    if greedy:
        return int(logits.argmax(-1))
    probs = torch.softmax(logits, -1).squeeze(0).numpy()
    return int((rng or np.random.default_rng()).choice(len(probs), p=probs))


def run_episode(task: str, size: int, seed: int, choose) -> dict:
    """Play one episode; ``choose(env, observation)`` returns an action. Records every frame."""
    env = make(task, size=size, seed=seed)
    observation = env.reset()
    optimal = env.optimal_steps()
    frames, total, steps = [observation], 0.0, 0
    actions, success = [], False
    while True:
        action = choose(env, observation)
        result = env.step(action)
        observation, total, steps = result.observation, total + result.reward, steps + 1
        frames.append(observation)
        actions.append(action)
        if result.terminated or result.truncated:
            success = bool(result.info.get("success"))
            break
    return {"success": success, "return": total, "steps": steps, "optimal_steps": optimal, "frames": frames, "actions": actions}


def evaluate(policy: str, task: str, size: int, episodes: int = 200, model: MultiTaskActorCritic | None = None, seed: int = 0) -> EvalResult:
    rng = np.random.default_rng(seed)
    if policy in ("ppo_greedy", "ppo_sampled"):
        if model is None:
            raise ValueError("A model is required to evaluate the PPO policy")
        model.eval()
        greedy = policy == "ppo_greedy"
        choose = lambda env, obs: policy_action(model, task, obs, greedy=greedy, rng=rng)  # noqa: E731
    elif policy == "random":
        choose = lambda env, obs: int(rng.integers(env.n_actions))  # noqa: E731
    elif policy == "oracle":
        choose = lambda env, obs: oracle_action(env)  # noqa: E731
    else:
        raise ValueError(f"Unknown policy '{policy}'")
    runs = [run_episode(task, size, EVAL_SEED_OFFSET + seed * episodes + i, choose) for i in range(episodes)]
    wins = [run for run in runs if run["success"]]
    return EvalResult(
        policy=policy, task=task, episodes=episodes,
        success_rate=len(wins) / episodes,
        mean_return=float(np.mean([run["return"] for run in runs])),
        mean_steps=float(np.mean([run["steps"] for run in runs])),
        optimality=float(np.mean([run["optimal_steps"] / run["steps"] for run in wins])) if wins else None,
    )


def compare(model: MultiTaskActorCritic, tasks, size: int, episodes: int = 200) -> list[dict]:
    return [asdict(evaluate(policy, task, size, episodes, model)) for task in tasks for policy in POLICIES]
