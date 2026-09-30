from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID, uuid4
from enum import Enum

class RoutingAlgorithm(str, Enum):
    DIJKSTRA = "dijkstra"
    RANDOM = "random"
    ECMP = "ecmp"
    RL_AGENT = "rl_agent"

class Node(BaseModel):
    id: str
    is_active: bool = True

class Link(BaseModel):
    source: str
    target: str
    capacity: int
    current_load: int = 0
    base_latency_ms: float
    queue_limit: int = 100
    loss_rate: float = 0.0
    is_active: bool = True

class Packet(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source: str
    target: str
    size: int
    creation_time: float
    path_taken: List[str] = Field(default_factory=list)
    delivered: bool = False
    dropped: bool = False
    drop_reason: Optional[str] = None
    latency_ms: float = 0.0

class TopologyType(str, Enum):
    RING = "ring"
    STAR = "star"
    MESH = "mesh"

class NetworkState(BaseModel):
    nodes: Dict[str, Node]
    links: List[Link]
    packets: List[Packet] = Field(default_factory=list)
    time_step: float = 0.0

class SimulationMetrics(BaseModel):
    algorithm: RoutingAlgorithm
    total_packets: int = 0
    delivered_packets: int = 0
    dropped_packets: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    throughput_packets: float = 0.0
    avg_link_utilization: float = 0.0
    max_link_utilization: float = 0.0
    energy_cost: float = 0.0
    seed: int = 0
    policy_version: Optional[str] = None


class TrainingResult(BaseModel):
    policy_version: str
    episodes: int
    seed: int
    final_mean_reward: float
    checksum: str
    reward_curve: List[float] = Field(default_factory=list)
