from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Flow:
    source: str
    dest: str
    weight: float = 1.0
    flow_type: str = "A"


@dataclass
class SimConfig:
    seed: int = 7
    mu: float = 1.0
    service_dist: str = "exponential"
    arrival_rate: float = 0.5
    arrival_dist: str = "exponential"
    pareto_alpha: float = 2.5
    flow_class_alphas: Dict[str, float] = field(
        default_factory=lambda: {"A": 3.0, "B": 1.5}
    )
    default_flow_type: str = "A"
    max_packets: int = 5000
    warmup_packets: int = 2000
    queue_bins: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 8, 13, 21)
    # Q-routing: Q(node, dest, next_hop) estimates the time to deliver via
    # next_hop, so costs are elapsed times and the future is not discounted.
    epsilon: float = 0.02
    alpha: float = 0.2
    gamma: float = 1.0
    q_state: str = "basic"  # "basic": (node, dest); "load": adds queue bins
    # Load-aware distance vector: extra cost per packet queued at a neighbor,
    # in units of that neighbor's mean service time.
    queue_weight: float = 1.0
    topology: str = "grid"
    grid_width: int = 4
    grid_height: int = 4
    edge_weight: float = 1.0
    edge_jitter: float = 0.2
    max_queue: Optional[int] = None
    max_hops: Optional[int] = None  # default: 4 x number of nodes
    drop_penalty: float = 100.0  # time units charged when a packet is dropped
    max_sim_time: Optional[float] = None
    neighbor_pad_value: int = -1
    dqn_hidden_sizes: Tuple[int, ...] = (64, 64)
    dqn_lr: float = 1e-3
    dqn_batch: int = 64
    dqn_buffer: int = 10000
    dqn_target_update: int = 200
    dqn_min_buffer: int = 200
    flows: List[Flow] = field(default_factory=list)


@dataclass
class ExperimentConfig:
    loads: List[float] = field(default_factory=lambda: [0.3, 0.6, 0.9, 1.1, 1.3])
    repeats: int = 3
    plot_path: str = "latency_vs_load.png"
