from dataclasses import dataclass
from typing import Dict, List, Tuple
import random


@dataclass
class Graph:
    nodes: List[str]
    edges: Dict[str, List[Tuple[str, float]]]

    def neighbors(self, node: str) -> List[Tuple[str, float]]:
        return self.edges.get(node, [])

    def edge_weight(self, src: str, dst: str) -> float:
        for neighbor, weight in self.edges.get(src, []):
            if neighbor == dst:
                return weight
        raise KeyError(f"missing edge {src} -> {dst}")


def _jittered(weight: float, jitter: float, rng: random.Random) -> float:
    if jitter <= 0.0:
        return weight
    return weight * (1.0 + rng.uniform(-jitter, jitter))


def make_grid(
    width: int,
    height: int,
    weight: float = 1.0,
    jitter: float = 0.2,
    seed: int = 7,
) -> Graph:
    rng = random.Random(seed)
    nodes = [f"n{r}_{c}" for r in range(height) for c in range(width)]
    edges: Dict[str, List[Tuple[str, float]]] = {node: [] for node in nodes}

    def add_edge(src: str, dst: str) -> None:
        edges[src].append((dst, _jittered(weight, jitter, rng)))

    for r in range(height):
        for c in range(width):
            node = f"n{r}_{c}"
            if r > 0:
                add_edge(node, f"n{r - 1}_{c}")
            if r < height - 1:
                add_edge(node, f"n{r + 1}_{c}")
            if c > 0:
                add_edge(node, f"n{r}_{c - 1}")
            if c < width - 1:
                add_edge(node, f"n{r}_{c + 1}")

    return Graph(nodes=nodes, edges=edges)


def make_fishnet() -> Graph:
    nodes = ["S1", "S2", "X1", "X2", "X3", "X4", "A", "B", "D"]
    edges: Dict[str, List[Tuple[str, float]]] = {
        "S1": [("X1", 1.0), ("X2", 1.2)],
        "S2": [("X2", 1.1), ("X3", 1.0)],
        "X1": [("X4", 1.0), ("A", 1.4)],
        "X2": [("X4", 0.9), ("X3", 1.0), ("B", 1.5)],
        "X3": [("X4", 0.9), ("D", 1.3)],
        "X4": [("A", 1.0), ("B", 1.0), ("D", 1.1)],
        "A": [],
        "B": [],
        "D": [],
    }
    return Graph(nodes=nodes, edges=edges)
