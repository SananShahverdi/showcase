"""Shared convolutional trunk with a learned task embedding and per-task heads."""

from __future__ import annotations

import torch
from torch import nn

from .envs import CHANNELS


class MultiTaskActorCritic(nn.Module):
    """One trunk for every task; each task gets its own policy and value head.

    A small learned task embedding is concatenated to the trunk features so the
    shared layers can condition on the task. (Adding a unit-variance embedding
    instead would drown the state features at initialization and make every
    state look alike.) Separate heads keep action spaces of different sizes apart.
    """

    def __init__(self, action_spaces: dict[str, int], size: int, hidden: int = 128, task_dim: int = 16):
        super().__init__()
        self.tasks = list(action_spaces)
        self.action_spaces = dict(action_spaces)
        self.size = size
        self.trunk = nn.Sequential(
            nn.Conv2d(CHANNELS, 32, kernel_size=3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 32, kernel_size=3, padding=1), nn.ReLU(),
            nn.Flatten(),
            nn.Linear(32 * size * size, hidden), nn.ReLU(),
        )
        self.task_embedding = nn.Embedding(len(self.tasks), task_dim)
        self.shared = nn.Sequential(nn.Linear(hidden + task_dim, hidden), nn.ReLU())
        self.policy_heads = nn.ModuleDict({task: nn.Linear(hidden, n) for task, n in action_spaces.items()})
        self.value_heads = nn.ModuleDict({task: nn.Linear(hidden, 1) for task in action_spaces})
        # Orthogonal initialization as in the reference PPO implementations: gain
        # sqrt(2) keeps ReLU activations from collapsing on sparse one-hot grids,
        # a small policy gain starts near-uniform, and the value head uses gain 1.
        for layer in [*self.trunk, *self.shared]:
            if isinstance(layer, (nn.Conv2d, nn.Linear)):
                nn.init.orthogonal_(layer.weight, gain=2 ** 0.5)
                nn.init.zeros_(layer.bias)
        for head in self.policy_heads.values():
            nn.init.orthogonal_(head.weight, gain=0.01)
            nn.init.zeros_(head.bias)
        for head in self.value_heads.values():
            nn.init.orthogonal_(head.weight, gain=1.0)
            nn.init.zeros_(head.bias)

    def forward(self, observations: torch.Tensor, task: str) -> tuple[torch.Tensor, torch.Tensor]:
        index = torch.full((observations.shape[0],), self.tasks.index(task), dtype=torch.long, device=observations.device)
        features = self.shared(torch.cat([self.trunk(observations), self.task_embedding(index)], dim=-1))
        return self.policy_heads[task](features), self.value_heads[task](features).squeeze(-1)

    def config(self) -> dict:
        return {"action_spaces": self.action_spaces, "size": self.size, "hidden": self.shared[0].out_features,
                "task_dim": self.task_embedding.embedding_dim}
