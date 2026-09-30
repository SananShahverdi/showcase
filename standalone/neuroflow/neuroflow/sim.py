"""Discrete-event simulation of a store-and-forward network of single-server queues.

Every node is a FIFO queue with one server (exponential or deterministic
service at rate mu). A packet queues and is served at each node it visits
except its destination, then crosses the chosen link with that link's fixed
delay. Routers pick the next hop when a packet joins a queue; learning
routers are told, on the packet's next arrival, how long that hop actually
took (waiting + service + link delay).
"""

from collections import deque
from dataclasses import dataclass
import heapq
import math
import random
from typing import Deque, Dict, List, Optional, Tuple

from .agents import BaseRouter
from .config import Flow, SimConfig
from .topology import Graph


@dataclass(order=True)
class Event:
    time: float
    seq: int
    kind: str
    node: Optional[str] = None
    packet: Optional["Packet"] = None
    flow_id: Optional[int] = None


@dataclass
class Packet:
    packet_id: int
    source: str
    dest: str
    flow_type: str
    created_time: float
    arrived_time: float = 0.0  # when the packet reached its current node
    hops: int = 0
    prev_state: Optional[Tuple] = None
    prev_action: Optional[str] = None
    next_hop: Optional[str] = None


class Node:
    def __init__(self, node_id: str, mu: float, max_queue: Optional[int]) -> None:
        self.node_id = node_id
        self.mu = mu
        self.max_queue = max_queue
        self.queue: Deque[Packet] = deque()
        self.busy = False
        self.busy_time = 0.0

    def system_size(self) -> int:
        return len(self.queue) + (1 if self.busy else 0)

    def can_accept(self) -> bool:
        if self.max_queue is None:
            return True
        return self.system_size() < self.max_queue


@dataclass
class SimulationResult:
    avg_latency: float
    p95_latency: float
    latencies: List[float]
    delivered: int
    dropped: int
    drop_rate: float
    mean_hops: float
    max_utilization: float
    sim_time: float


def queue_bin(level: int, bins: Tuple[int, ...]) -> int:
    for idx, threshold in enumerate(bins):
        if level <= threshold:
            return idx
    return len(bins)


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * q
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


class DiscreteEventSimulator:
    def __init__(self, graph: Graph, router: BaseRouter, config: SimConfig, rng: random.Random) -> None:
        self.graph = graph
        self.router = router
        self.config = config
        self.rng = rng
        self.nodes: Dict[str, Node] = {node: Node(node, config.mu, config.max_queue) for node in graph.nodes}
        self.neighbor_order = {node: sorted(neighbor for neighbor, _ in graph.neighbors(node)) for node in graph.nodes}
        self.max_degree = max((len(neighbors) for neighbors in self.neighbor_order.values()), default=0)
        self.max_hops = config.max_hops or 4 * len(graph.nodes)
        self.event_queue: List[Event] = []
        self.event_seq = 0
        self.time = 0.0
        self.packet_id = 0
        self.finished = 0  # delivered + dropped, used for warm-up accounting
        self.delivered = 0
        self.dropped = 0
        self.measured_dropped = 0
        self.latencies: List[float] = []
        self.hop_counts: List[int] = []
        self.flow_rates = self._build_flow_rates(config.flows)

    def _flow_alpha(self, flow_type: str) -> float:
        return self.config.flow_class_alphas.get(flow_type, self.config.pareto_alpha)

    def _build_flow_rates(self, flows: List[Flow]) -> List[Tuple[str, str, float, str, float]]:
        total_weight = sum(flow.weight for flow in flows)
        if not flows or total_weight <= 0:
            return []
        scale = self.config.arrival_rate / total_weight
        return [(flow.source, flow.dest, flow.weight * scale, flow.flow_type, self._flow_alpha(flow.flow_type)) for flow in flows]

    def _schedule(self, time: float, kind: str, node: Optional[str], packet: Optional[Packet], flow_id: Optional[int] = None) -> None:
        heapq.heappush(self.event_queue, Event(time, self.event_seq, kind, node, packet, flow_id))
        self.event_seq += 1

    def _node_loads(self) -> Dict[str, int]:
        return {node_id: node.system_size() for node_id, node in self.nodes.items()}

    def _neighbor_bins(self, node_id: str) -> Tuple[int, ...]:
        bins = [queue_bin(self.nodes[neighbor].system_size(), self.config.queue_bins) for neighbor in self.neighbor_order[node_id]]
        bins += [self.config.neighbor_pad_value] * (self.max_degree - len(bins))
        return tuple(bins)

    def _state(self, node_id: str, dest: str, flow_type: str, load: int) -> Tuple:
        return (node_id, dest, flow_type, queue_bin(load, self.config.queue_bins), self._neighbor_bins(node_id))

    def _start_service(self, node: Node) -> None:
        if not node.queue:
            node.busy = False
            return
        packet = node.queue.popleft()
        node.busy = True
        service_time = 1.0 / node.mu if self.config.service_dist == "deterministic" else self.rng.expovariate(node.mu)
        node.busy_time += service_time
        self._schedule(self.time + service_time, "departure", node.node_id, packet)

    def _measuring(self) -> bool:
        return self.finished >= self.config.warmup_packets

    def _finish(self, packet: Packet, delivered: bool) -> None:
        measuring = self._measuring()
        self.finished += 1
        if delivered:
            self.delivered += 1
            if measuring:
                self.latencies.append(self.time - packet.created_time)
                self.hop_counts.append(packet.hops)
        else:
            self.dropped += 1
            if measuring:
                self.measured_dropped += 1

    def _sample_interarrival(self, rate: float, alpha: Optional[float] = None) -> Optional[float]:
        if rate <= 0:
            return None
        if self.config.arrival_dist == "pareto":
            shape = alpha if alpha is not None else self.config.pareto_alpha
            scale = (shape - 1.0) / (shape * rate)  # mean interarrival = 1 / rate
            return scale * self.rng.paretovariate(shape)
        return self.rng.expovariate(rate)

    def _handle_external_arrival(self, flow_id: int) -> None:
        source, dest, rate, flow_type, alpha = self.flow_rates[flow_id]
        packet = Packet(self.packet_id, source, dest, flow_type, created_time=self.time, arrived_time=self.time)
        self.packet_id += 1
        self._schedule(self.time, "arrival", source, packet)
        interarrival = self._sample_interarrival(rate, alpha)
        if interarrival is not None:
            self._schedule(self.time + interarrival, "external_arrival", None, None, flow_id)

    def _handle_arrival(self, node_id: str, packet: Packet) -> None:
        node = self.nodes[node_id]
        load = node.system_size()
        neighbors = self.graph.neighbors(node_id)
        terminal = node_id == packet.dest
        drop = not terminal and (not node.can_accept() or not neighbors or packet.hops >= self.max_hops)

        if packet.prev_state is not None:
            hop_time = self.time - packet.arrived_time
            if terminal:
                self.router.observe_transition(packet.prev_state, packet.prev_action, cost=hop_time,
                                               next_state=None, next_actions=[], terminal=True)
            elif drop:
                self.router.observe_transition(packet.prev_state, packet.prev_action, cost=hop_time + self.config.drop_penalty,
                                               next_state=None, next_actions=[], terminal=True)
            else:
                self.router.observe_transition(packet.prev_state, packet.prev_action, cost=hop_time,
                                               next_state=self._state(node_id, packet.dest, packet.flow_type, load),
                                               next_actions=[neighbor for neighbor, _ in neighbors], terminal=False)
        packet.arrived_time = self.time

        if terminal:
            self._finish(packet, delivered=True)
            return
        if drop:
            self._finish(packet, delivered=False)
            return

        state = self._state(node_id, packet.dest, packet.flow_type, load)
        next_hop = self.router.select_next_hop(state=state, node=node_id, dest=packet.dest, neighbors=neighbors,
                                               graph=self.graph, rng=self.rng, node_loads=self._node_loads())
        packet.prev_state, packet.prev_action, packet.next_hop = state, next_hop, next_hop
        node.queue.append(packet)
        if not node.busy:
            self._start_service(node)

    def _handle_departure(self, node_id: str, packet: Packet) -> None:
        node = self.nodes[node_id]
        node.busy = False
        if node.queue:
            self._start_service(node)
        packet.hops += 1
        delay = self.graph.edge_weight(node_id, packet.next_hop)
        self._schedule(self.time + delay, "arrival", packet.next_hop, packet)

    def run(self) -> SimulationResult:
        if not self.flow_rates:
            raise ValueError("configure at least one flow with positive weight")
        for flow_id, (_, _, rate, _, alpha) in enumerate(self.flow_rates):
            interarrival = self._sample_interarrival(rate, alpha)
            if interarrival is not None:
                self._schedule(interarrival, "external_arrival", None, None, flow_id)

        target = self.config.max_packets + self.config.warmup_packets
        while self.finished < target and self.event_queue:
            event = heapq.heappop(self.event_queue)
            if self.config.max_sim_time is not None and event.time > self.config.max_sim_time:
                break
            self.time = event.time
            if event.kind == "external_arrival":
                self._handle_external_arrival(event.flow_id)
            elif event.kind == "arrival":
                self._handle_arrival(event.node, event.packet)
            elif event.kind == "departure":
                self._handle_departure(event.node, event.packet)

        measured = len(self.latencies) + self.measured_dropped
        return SimulationResult(
            avg_latency=sum(self.latencies) / len(self.latencies) if self.latencies else float("nan"),
            p95_latency=percentile(self.latencies, 0.95),
            latencies=self.latencies,
            delivered=self.delivered,
            dropped=self.dropped,
            drop_rate=self.measured_dropped / measured if measured else 0.0,
            mean_hops=sum(self.hop_counts) / len(self.hop_counts) if self.hop_counts else float("nan"),
            max_utilization=max(node.busy_time for node in self.nodes.values()) / self.time if self.time else 0.0,
            sim_time=self.time,
        )
