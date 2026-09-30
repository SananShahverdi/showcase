import random
from typing import List, Optional, Tuple

import networkx as nx

from network_digital_twin_rl_routing_optimizer.domain.models import Link, NetworkState, Node, TopologyType


class NetworkSimulator:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.state = NetworkState(nodes={}, links=[])

    def build_topology(self, topo_type: TopologyType, num_nodes: int = 5):
        if num_nodes < 3 or num_nodes > 100:
            raise ValueError("num_nodes must be between 3 and 100")
        self.graph.clear()
        if topo_type == TopologyType.RING:
            generated = nx.cycle_graph(num_nodes, create_using=nx.DiGraph)
            generated.add_edges_from([(v, u) for u, v in list(generated.edges())])
        elif topo_type == TopologyType.STAR:
            generated = nx.star_graph(num_nodes - 1).to_directed()
        else:
            generated = nx.complete_graph(num_nodes, create_using=nx.DiGraph)

        nodes = {f"n{node}": Node(id=f"n{node}") for node in generated.nodes()}
        self.graph.add_nodes_from(nodes)
        links: List[Link] = []
        for source, target in generated.edges():
            source_id, target_id = f"n{source}", f"n{target}"
            link = Link(source=source_id, target=target_id, capacity=100, base_latency_ms=10.0)
            links.append(link)
            self.graph.add_edge(
                source_id,
                target_id,
                capacity=link.capacity,
                current_load=0,
                weight=link.base_latency_ms,
                base_latency_ms=link.base_latency_ms,
                queue_limit=link.queue_limit,
                loss_rate=link.loss_rate,
            )
        self.state = NetworkState(nodes=nodes, links=links)

    def fail_link(self, source: str, target: str):
        link = self._find_link(source, target)
        if not link:
            raise ValueError("Link not found")
        link.is_active = False
        if self.graph.has_edge(source, target):
            self.graph.remove_edge(source, target)

    def recover_link(self, source: str, target: str):
        link = self._find_link(source, target)
        if not link:
            raise ValueError("Link not found")
        if link.is_active:
            return
        link.is_active = True
        self.graph.add_edge(
            source,
            target,
            capacity=link.capacity,
            current_load=link.current_load,
            weight=link.base_latency_ms,
            base_latency_ms=link.base_latency_ms,
            queue_limit=link.queue_limit,
            loss_rate=link.loss_rate,
        )

    def reset_runtime(self):
        self.state.packets.clear()
        self.state.time_step = 0
        for link in self.state.links:
            link.current_load = 0
            if link.is_active and self.graph.has_edge(link.source, link.target):
                self.graph[link.source][link.target]["current_load"] = 0
                self.graph[link.source][link.target]["weight"] = link.base_latency_ms

    def advance(self, decay: float = 0.75):
        self.state.time_step += 1
        for link in self.state.links:
            link.current_load = max(0, int(link.current_load * decay))
            if link.is_active and self.graph.has_edge(link.source, link.target):
                self.graph[link.source][link.target]["current_load"] = link.current_load
                self.graph[link.source][link.target]["weight"] = self.effective_latency(link.source, link.target)

    def apply_path(self, path: List[str], packet_size: int, rng: random.Random) -> Tuple[bool, float, Optional[str]]:
        latency = 0.0
        traversed: List[Link] = []
        for source, target in zip(path, path[1:]):
            link = self._find_link(source, target)
            if not link or not link.is_active or not self.graph.has_edge(source, target):
                return False, 0.0, "link_unavailable"
            if link.current_load + packet_size > link.capacity + link.queue_limit:
                return False, 0.0, "queue_overflow"
            if rng.random() < link.loss_rate:
                return False, 0.0, "link_loss"
            utilization = min((link.current_load + packet_size) / link.capacity, 2.0)
            latency += link.base_latency_ms * (1 + utilization * utilization * 3)
            traversed.append(link)
        for link in traversed:
            link.current_load += packet_size
            self.graph[link.source][link.target]["current_load"] = link.current_load
        return True, latency, None

    def effective_latency(self, source: str, target: str) -> float:
        link = self._find_link(source, target)
        if not link:
            return float("inf")
        utilization = min(link.current_load / max(link.capacity, 1), 2.0)
        return link.base_latency_ms * (1 + utilization * utilization * 3)

    def utilizations(self) -> List[float]:
        return [link.current_load / max(link.capacity, 1) for link in self.state.links if link.is_active]

    def _find_link(self, source: str, target: str) -> Optional[Link]:
        return next((link for link in self.state.links if link.source == source and link.target == target), None)

    def get_active_graph(self) -> nx.DiGraph:
        return self.graph
