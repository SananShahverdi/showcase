import hashlib
import json
import random
from collections import defaultdict
from typing import DefaultDict, List, Optional, Tuple

import networkx as nx

from network_digital_twin_rl_routing_optimizer.domain.models import TrainingResult

StateAction = Tuple[str, str, str]


class QLearningRouter:
    """Small-graph tabular Q-learning policy with safe loop/no-path handling."""

    def __init__(self):
        self.q: DefaultDict[StateAction, float] = defaultdict(float)
        self.policy_version: Optional[str] = None
        self.checksum: Optional[str] = None

    def train(
        self,
        graph: nx.DiGraph,
        episodes: int = 500,
        seed: int = 42,
        learning_rate: float = 0.25,
        discount: float = 0.9,
    ) -> TrainingResult:
        if len(graph) < 2:
            raise ValueError("Build a topology before training")
        if episodes < 20 or episodes > 50_000:
            raise ValueError("episodes must be between 20 and 50000")
        rng = random.Random(seed)
        nodes = sorted(graph.nodes())
        curve: List[float] = []
        self.q.clear()
        for episode in range(episodes):
            source, target = rng.sample(nodes, 2)
            current = source
            visited = {source}
            total_reward = 0.0
            epsilon = max(0.05, 1.0 - episode / max(episodes * 0.8, 1))
            for _ in range(len(nodes) * 2):
                neighbors = sorted(graph.successors(current))
                if not neighbors:
                    total_reward -= 100
                    break
                if rng.random() < epsilon:
                    action = rng.choice(neighbors)
                else:
                    action = max(neighbors, key=lambda node: (self.q[(current, target, node)], node))
                edge = graph[current][action]
                latency = float(edge.get("weight", edge.get("base_latency_ms", 10.0)))
                reward = 100.0 if action == target else -latency
                if action in visited and action != target:
                    reward -= 25.0
                future = 0.0
                if action != target:
                    next_neighbors = list(graph.successors(action))
                    future = max((self.q[(action, target, nxt)] for nxt in next_neighbors), default=-100.0)
                key = (current, target, action)
                self.q[key] += learning_rate * (reward + discount * future - self.q[key])
                total_reward += reward
                current = action
                if current == target:
                    break
                visited.add(current)
            curve.append(total_reward)
        serialized = {"|".join(key): round(value, 8) for key, value in sorted(self.q.items())}
        self.checksum = hashlib.sha256(json.dumps(serialized, sort_keys=True).encode()).hexdigest()
        self.policy_version = f"q-{self.checksum[:12]}"
        tail = curve[-min(50, len(curve)):]
        return TrainingResult(
            policy_version=self.policy_version,
            episodes=episodes,
            seed=seed,
            final_mean_reward=sum(tail) / len(tail),
            checksum=self.checksum,
            reward_curve=curve,
        )

    def get_path(self, graph: nx.DiGraph, source: str, target: str) -> Optional[List[str]]:
        if not self.policy_version or source not in graph or target not in graph:
            return None
        current = source
        path = [source]
        visited = {source}
        for _ in range(len(graph)):
            neighbors = [node for node in graph.successors(current) if node not in visited or node == target]
            scored = [(self.q.get((current, target, node)), node) for node in neighbors]
            scored = [(score, node) for score, node in scored if score is not None]
            if not scored:
                return None
            _, current = max(scored, key=lambda item: (item[0], item[1]))
            path.append(current)
            if current == target:
                return path
            visited.add(current)
        return None
