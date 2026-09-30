"""Static routing analysis: shortest paths, distances, and per-node offered load."""

import heapq
from typing import Dict, List, Tuple

from .config import Flow
from .topology import Graph


def shortest_distances(graph: Graph) -> Dict[str, Dict[str, float]]:
    """dist[source][dest] by Dijkstra over link delays (inf when unreachable)."""
    result: Dict[str, Dict[str, float]] = {}
    for source in graph.nodes:
        dist = {node: float("inf") for node in graph.nodes}
        dist[source] = 0.0
        heap: List[Tuple[float, str]] = [(0.0, source)]
        while heap:
            current, node = heapq.heappop(heap)
            if current != dist[node]:
                continue
            for neighbor, weight in graph.neighbors(node):
                candidate = current + weight
                if candidate < dist[neighbor]:
                    dist[neighbor] = candidate
                    heapq.heappush(heap, (candidate, neighbor))
        result[source] = dist
    return result


def next_hops(graph: Graph, dist: Dict[str, Dict[str, float]]) -> Dict[Tuple[str, str], str]:
    """Shortest-path next hop for every (node, dest) pair that is reachable."""
    table: Dict[Tuple[str, str], str] = {}
    for node in graph.nodes:
        for dest in graph.nodes:
            if node == dest:
                continue
            best = min(
                ((weight + dist[neighbor][dest], neighbor) for neighbor, weight in graph.neighbors(node)),
                default=(float("inf"), None),
            )
            if best[1] is not None and best[0] < float("inf"):
                table[(node, dest)] = best[1]
    return table


def shortest_path(graph: Graph, source: str, dest: str) -> List[str]:
    hops = next_hops(graph, shortest_distances(graph))
    path = [source]
    while path[-1] != dest:
        path.append(hops[(path[-1], dest)])
    return path


def shortest_path_loads(graph: Graph, flows: List[Flow], total_rate: float) -> Dict[str, float]:
    """Packets per unit time served at each node when every flow follows its shortest path.

    Every node on the path except the destination queues and serves the packet.
    """
    total_weight = sum(flow.weight for flow in flows)
    hops = next_hops(graph, shortest_distances(graph))
    loads = {node: 0.0 for node in graph.nodes}
    for flow in flows:
        rate = total_rate * flow.weight / total_weight
        node = flow.source
        while node != flow.dest:
            loads[node] += rate
            node = hops[(node, flow.dest)]
    return loads


def rate_for_bottleneck_load(graph: Graph, flows: List[Flow], mu: float, load: float) -> float:
    """Total arrival rate at which the busiest node under shortest-path routing runs at `load` x capacity."""
    unit = shortest_path_loads(graph, flows, 1.0)
    return load * mu / max(unit.values())
