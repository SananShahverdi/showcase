"""Train, evaluate, and save a multi-task PPO agent.

    python -m multitask_ppo_lab.cli train --updates 250 --out artifacts
    python -m multitask_ppo_lab.cli evaluate --out artifacts
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, fields
from pathlib import Path

import torch

from multitask_ppo_lab.algorithms.evaluation import compare
from multitask_ppo_lab.algorithms.network import MultiTaskActorCritic
from multitask_ppo_lab.algorithms.ppo import PPOConfig, config_dict, train


def save(model: MultiTaskActorCritic, config: PPOConfig, history, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "model": model.config(), "training": config_dict(config)}, out / "policy.pt")
    (out / "history.json").write_text(json.dumps([asdict(item) for item in history], indent=1))


def load(out: Path) -> tuple[MultiTaskActorCritic, dict]:
    checkpoint = torch.load(out / "policy.pt", map_location="cpu", weights_only=True)
    model = MultiTaskActorCritic(**checkpoint["model"])
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model, checkpoint["training"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["train", "evaluate"])
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    parser.add_argument("--episodes", type=int, default=200, help="Held-out evaluation episodes per task and policy")
    parser.add_argument("--threads", type=int, default=4)
    for item in fields(PPOConfig):
        if item.name != "tasks":
            kind = (lambda value: value.lower() in ("1", "true", "yes")) if isinstance(item.default, bool) else type(item.default)
            parser.add_argument(f"--{item.name.replace('_', '-')}", type=kind, default=item.default)
    args = parser.parse_args(argv)
    torch.set_num_threads(args.threads)

    if args.command == "train":
        config = PPOConfig(**{item.name: getattr(args, item.name) for item in fields(PPOConfig) if item.name != "tasks"})

        def progress(stats):
            summary = "  ".join(f"{task}: success {values['success_rate']}, return {values['mean_return']}" for task, values in stats.per_task.items())
            print(f"update {stats.update:4d}  steps {stats.env_steps:8d}  {stats.seconds:7.1f}s  {summary}", flush=True)

        model, history = train(config, on_update=progress)
        save(model, config, history, args.out)
        size = config.size
    else:
        model, training = load(args.out)
        size = training["size"]
    results = compare(model, model.tasks, size, args.episodes)
    (args.out / "evaluation.json").write_text(json.dumps(results, indent=1))
    for row in results:
        print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
