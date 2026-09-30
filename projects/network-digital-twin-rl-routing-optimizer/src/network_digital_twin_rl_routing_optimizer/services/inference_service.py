import math
import random
from typing import Dict, List, Optional

from network_digital_twin_rl_routing_optimizer.algorithms.baselines import RoutingLogic
from network_digital_twin_rl_routing_optimizer.algorithms.q_learning import QLearningRouter
from network_digital_twin_rl_routing_optimizer.algorithms.simulator import NetworkSimulator
from network_digital_twin_rl_routing_optimizer.domain.models import Packet, RoutingAlgorithm, SimulationMetrics, TrainingResult
from network_digital_twin_rl_routing_optimizer.services.training_service import TrainingService


class InferenceService:
    def __init__(self, simulator: NetworkSimulator, training_service: TrainingService):
        self.simulator = simulator
        self.training_service = training_service
        self.policy = QLearningRouter()
        # The most recent training run and the comparison made with that policy,
        # so a console opened later shows the current lab instead of an empty one.
        self.latest_training: Optional[TrainingResult] = None
        self.latest_comparison: Optional[Dict[str, object]] = None

    def reset(self) -> None:
        """Forget the trained policy and its results (used when the topology is rebuilt)."""
        self.policy = QLearningRouter()
        self.latest_training = None
        self.latest_comparison = None

    def train_policy(self, episodes: int = 500, seed: int = 42) -> TrainingResult:
        result = self.policy.train(self.simulator.get_active_graph(), episodes=episodes, seed=seed)
        self.training_service.log_training(result)
        self.latest_training = result
        # A comparison made with the previous policy no longer describes this one.
        self.latest_comparison = None
        return result

    def latest(self) -> Dict[str, object]:
        return {"training": self.latest_training, "comparison": self.latest_comparison}

    def route(self, algorithm: RoutingAlgorithm, source: str, target: str, seed: int = 42) -> Optional[List[str]]:
        if algorithm == RoutingAlgorithm.RL_AGENT and not self.policy.policy_version:
            raise ValueError("Train a policy before RL inference")
        return RoutingLogic.get_path(
            algorithm,
            self.simulator.get_active_graph(),
            source,
            target,
            rng=random.Random(seed),
            policy=self.policy.get_path,
        )

    def run_evaluation(self, algo: RoutingAlgorithm, num_packets: int = 100, seed: int = 42) -> SimulationMetrics:
        graph = self.simulator.get_active_graph()
        nodes = sorted(graph.nodes())
        if len(nodes) < 2:
            raise ValueError("Build a topology before evaluation")
        if algo == RoutingAlgorithm.RL_AGENT and not self.policy.policy_version:
            raise ValueError("Train a policy before evaluating RL_AGENT")
        if num_packets < 1 or num_packets > 100_000:
            raise ValueError("num_packets must be between 1 and 100000")
        self.simulator.reset_runtime()
        rng = random.Random(seed)
        traffic = [rng.sample(nodes, 2) for _ in range(num_packets)]
        metrics = SimulationMetrics(
            algorithm=algo,
            total_packets=num_packets,
            seed=seed,
            policy_version=self.policy.policy_version if algo == RoutingAlgorithm.RL_AGENT else None,
        )
        latencies: List[float] = []
        utilization_samples: List[float] = []
        for source, target in traffic:
            packet = Packet(source=source, target=target, size=10, creation_time=self.simulator.state.time_step)
            path = RoutingLogic.get_path(algo, graph, source, target, rng=rng, policy=self.policy.get_path)
            delivered, latency, reason = self.simulator.apply_path(path, packet.size, rng) if path else (False, 0.0, "no_path")
            packet.path_taken = path or []
            packet.delivered = delivered
            packet.dropped = not delivered
            packet.drop_reason = reason
            packet.latency_ms = latency
            if delivered:
                metrics.delivered_packets += 1
                metrics.energy_cost += len(path or []) - 1
                latencies.append(latency)
            else:
                metrics.dropped_packets += 1
            self.simulator.state.packets.append(packet)
            utilization_samples.extend(self.simulator.utilizations())
            self.simulator.advance()
        if latencies:
            ordered = sorted(latencies)
            metrics.avg_latency_ms = sum(ordered) / len(ordered)
            metrics.p95_latency_ms = ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)]
        if utilization_samples:
            metrics.avg_link_utilization = sum(utilization_samples) / len(utilization_samples)
            metrics.max_link_utilization = max(utilization_samples)
        metrics.throughput_packets = metrics.delivered_packets / max(self.simulator.state.time_step, 1)
        self.training_service.log_experiment(f"eval-{algo.value}-{seed}-{num_packets}", metrics)
        return metrics

    def compare(self, algorithms: List[RoutingAlgorithm], num_packets: int, seed: int) -> Dict[str, object]:
        if len(set(algorithms)) != len(algorithms):
            raise ValueError("Algorithms in a comparison must be unique")
        results = {algorithm.value: self.run_evaluation(algorithm, num_packets, seed) for algorithm in algorithms}
        comparison = {
            "seed": seed,
            "num_packets": num_packets,
            "results": {name: metrics.model_dump(mode="json") for name, metrics in results.items()},
        }
        self.latest_comparison = comparison
        return comparison
