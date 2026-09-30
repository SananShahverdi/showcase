import random
from typing import Callable, List, Optional

import networkx as nx

from network_digital_twin_rl_routing_optimizer.domain.models import RoutingAlgorithm


class RoutingLogic:
    @staticmethod
    def get_path(
        algo: RoutingAlgorithm,
        graph: nx.DiGraph,
        source: str,
        target: str,
        rng: Optional[random.Random] = None,
        policy: Optional[Callable[[nx.DiGraph, str, str], Optional[List[str]]]] = None,
    ) -> Optional[List[str]]:
        if not graph.has_node(source) or not graph.has_node(target):
            return None
        chooser = rng or random.Random()
        try:
            if algo == RoutingAlgorithm.DIJKSTRA:
                return nx.shortest_path(graph, source=source, target=target, weight="weight")
            if algo == RoutingAlgorithm.ECMP:
                paths = list(nx.all_shortest_paths(graph, source=source, target=target, weight="weight"))
                return chooser.choice(paths) if paths else None
            if algo == RoutingAlgorithm.RANDOM:
                paths = list(nx.all_simple_paths(graph, source=source, target=target, cutoff=min(8, len(graph))))
                return chooser.choice(paths) if paths else None
            if algo == RoutingAlgorithm.RL_AGENT:
                return policy(graph, source, target) if policy else None
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        return None
