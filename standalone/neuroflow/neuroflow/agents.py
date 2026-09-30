from collections import deque
from typing import Deque, Dict, List, Tuple

from .analysis import next_hops, shortest_distances
from .topology import Graph


def _require_torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is required for DQNRouter. Install with 'pip install torch'."
        ) from exc
    return torch


class BaseRouter:
    name = "base"

    def observe_transition(
        self,
        prev_state,
        prev_action,
        cost,
        next_state,
        next_actions,
        terminal,
    ) -> None:
        return None

    def select_next_hop(
        self,
        state,
        node,
        dest,
        neighbors: List[Tuple[str, float]],
        graph: Graph,
        rng,
        node_loads,
    ) -> str:
        raise NotImplementedError


class QLearningRouter(BaseRouter):
    """Q-routing (Boyan and Littman, 1994).

    Q(x, d, y) estimates the time for a packet at node x bound for d to be
    delivered if it is sent to neighbor y. Each hop reports how long it
    actually took (queueing + service + link delay), and the estimate is
    moved toward that time plus y's best remaining estimate. With
    ``q_state="load"`` the key also includes local and neighbor queue bins.
    """

    name = "q_learning"

    def __init__(self, alpha: float, gamma: float, epsilon: float, q_state: str = "basic") -> None:
        if q_state not in {"basic", "load"}:
            raise ValueError("q_state must be 'basic' or 'load'")
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_state = q_state
        self.q: Dict[Tuple[Tuple, str], float] = {}

    def _key(self, state) -> Tuple:
        return state[:2] if self.q_state == "basic" else state

    def _get_q(self, state, action) -> float:
        return self.q.get((self._key(state), action), 0.0)

    def _min_next_q(self, next_state, next_actions) -> float:
        if not next_actions:
            return 0.0
        return min(self._get_q(next_state, action) for action in next_actions)

    def observe_transition(self, prev_state, prev_action, cost, next_state, next_actions, terminal) -> None:
        target = cost
        if not terminal:
            target += self.gamma * self._min_next_q(next_state, next_actions)
        key = (self._key(prev_state), prev_action)
        old = self.q.get(key, 0.0)
        self.q[key] = old + self.alpha * (target - old)

    def select_next_hop(self, state, node, dest, neighbors: List[Tuple[str, float]], graph: Graph, rng, node_loads) -> str:
        if rng.random() < self.epsilon:
            return rng.choice([neighbor for neighbor, _ in neighbors])
        # Unvisited estimates are 0, which is optimistic: every hop is tried before it is ruled out.
        return min(neighbors, key=lambda item: self._get_q(state, item[0]))[0]


class DQNRouter(BaseRouter):
    name = "dqn"

    def __init__(self, graph: Graph, config, rng) -> None:
        torch = _require_torch()
        self.torch = torch
        self.graph = graph
        self.config = config
        self.rng = rng
        self.node_to_idx = {node: idx for idx, node in enumerate(graph.nodes)}
        self.idx_to_node = {idx: node for node, idx in self.node_to_idx.items()}
        self.flow_types = sorted(config.flow_class_alphas.keys())
        if config.default_flow_type not in self.flow_types:
            self.flow_types.append(config.default_flow_type)
        self.flow_to_idx = {flow_type: idx for idx, flow_type in enumerate(self.flow_types)}
        self.max_nodes = len(graph.nodes)
        self.max_degree = max(
            (len(graph.neighbors(node)) for node in graph.nodes), default=0
        )
        self.max_bin = max(len(config.queue_bins), 1)
        self.device = torch.device("cpu")
        self.torch.manual_seed(config.seed)
        input_dim = 2 * self.max_nodes + len(self.flow_types) + 1 + self.max_degree
        self.net = _build_mlp(input_dim, config.dqn_hidden_sizes, self.max_nodes)
        self.target_net = _build_mlp(input_dim, config.dqn_hidden_sizes, self.max_nodes)
        self.target_net.load_state_dict(self.net.state_dict())
        self.target_net.eval()
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=config.dqn_lr)
        self.loss_fn = torch.nn.MSELoss()
        self.buffer: Deque = deque(maxlen=config.dqn_buffer)
        self.steps = 0

    def _normalize_bin(self, value: int) -> float:
        if value == self.config.neighbor_pad_value:
            return -1.0
        return float(value) / float(self.max_bin)

    def _state_vector(self, state) -> "torch.Tensor":
        node_id, dest_id, flow_type, local_bin, neighbor_bins = state
        size = 2 * self.max_nodes + len(self.flow_types) + 1 + self.max_degree
        vec = [0.0] * size
        node_idx = self.node_to_idx[node_id]
        dest_idx = self.node_to_idx[dest_id]
        vec[node_idx] = 1.0
        vec[self.max_nodes + dest_idx] = 1.0
        flow_offset = 2 * self.max_nodes
        flow_idx = self.flow_to_idx.get(flow_type)
        if flow_idx is not None:
            vec[flow_offset + flow_idx] = 1.0
        local_offset = flow_offset + len(self.flow_types)
        vec[local_offset] = self._normalize_bin(local_bin)
        offset = local_offset + 1
        for idx in range(self.max_degree):
            if idx < len(neighbor_bins):
                value = neighbor_bins[idx]
            else:
                value = self.config.neighbor_pad_value
            vec[offset + idx] = self._normalize_bin(value)
        return self.torch.tensor(vec, dtype=self.torch.float32, device=self.device)

    def _min_next_q(self, next_state, next_actions) -> float:
        if not next_actions:
            return 0.0
        next_vec = self._state_vector(next_state).unsqueeze(0)
        with self.torch.no_grad():
            q_values = self.target_net(next_vec).squeeze(0)
        indices = [self.node_to_idx[action] for action in next_actions]
        return float(self.torch.min(q_values[indices]).item())

    def observe_transition(
        self,
        prev_state,
        prev_action,
        cost,
        next_state,
        next_actions,
        terminal,
    ) -> None:
        if prev_state is None or prev_action is None:
            return
        if prev_action not in self.node_to_idx:
            return
        state_vec = self._state_vector(prev_state)
        action_idx = self.node_to_idx[prev_action]
        if terminal or next_state is None:
            next_vec = None
            next_action_indices: List[int] = []
        else:
            next_vec = self._state_vector(next_state)
            next_action_indices = [
                self.node_to_idx[action]
                for action in next_actions
                if action in self.node_to_idx
            ]
        self.buffer.append(
            (state_vec, action_idx, float(cost), next_vec, next_action_indices, terminal)
        )
        self._train_step()

    def _train_step(self) -> None:
        if len(self.buffer) < self.config.dqn_min_buffer:
            return
        batch_size = min(self.config.dqn_batch, len(self.buffer))
        batch = self.rng.sample(self.buffer, batch_size)
        state_batch = self.torch.stack([item[0] for item in batch])
        action_batch = self.torch.tensor(
            [item[1] for item in batch], dtype=self.torch.long
        )
        cost_batch = self.torch.tensor(
            [item[2] for item in batch], dtype=self.torch.float32
        )

        q_values = self.net(state_batch)
        q_selected = q_values.gather(1, action_batch.unsqueeze(1)).squeeze(1)

        targets = []
        with self.torch.no_grad():
            for _, _, cost, next_vec, next_actions, terminal in batch:
                if terminal or next_vec is None or not next_actions:
                    targets.append(cost)
                else:
                    next_q = self.target_net(next_vec.unsqueeze(0)).squeeze(0)
                    min_next = self.torch.min(next_q[next_actions]).item()
                    targets.append(cost + self.config.gamma * min_next)
        target_batch = self.torch.tensor(targets, dtype=self.torch.float32)

        loss = self.loss_fn(q_selected, target_batch)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.steps += 1
        if self.steps % self.config.dqn_target_update == 0:
            self.target_net.load_state_dict(self.net.state_dict())

    def select_next_hop(
        self,
        state,
        node,
        dest,
        neighbors: List[Tuple[str, float]],
        graph: Graph,
        rng,
        node_loads,
    ) -> str:
        if rng.random() < self.config.epsilon:
            return rng.choice([neighbor for neighbor, _ in neighbors])
        state_vec = self._state_vector(state).unsqueeze(0)
        with self.torch.no_grad():
            q_values = self.net(state_vec).squeeze(0)
        neighbor_ids = [neighbor for neighbor, _ in neighbors]
        neighbor_indices = [self.node_to_idx[neighbor] for neighbor in neighbor_ids]
        best_idx = min(neighbor_indices, key=lambda idx: float(q_values[idx].item()))
        return self.idx_to_node[best_idx]


class DistanceVectorRouter(BaseRouter):
    """Distance-vector routing with an optional queue-delay term.

    Distances to every destination come from converged Bellman-Ford tables
    (identical to Dijkstra). The next hop minimizes
    ``link delay + neighbor distance + queue_weight * neighbor queue / mu``;
    with ``queue_weight=0`` this is plain shortest-path routing.
    """

    name = "distance_vector"

    def __init__(self, graph: Graph, queue_weight: float, mu: float) -> None:
        self.queue_weight = queue_weight
        self.mu = mu
        self.dist = shortest_distances(graph)

    def select_next_hop(self, state, node, dest, neighbors: List[Tuple[str, float]], graph: Graph, rng, node_loads) -> str:
        def cost(item):
            neighbor, weight = item
            return weight + self.dist[neighbor][dest] + self.queue_weight * node_loads.get(neighbor, 0) / self.mu
        return min(neighbors, key=cost)[0]


class DijkstraRouter(BaseRouter):
    """Static shortest-path routing on link delays."""

    name = "dijkstra"

    def __init__(self, graph: Graph) -> None:
        self.next_hop = next_hops(graph, shortest_distances(graph))

    def select_next_hop(self, state, node, dest, neighbors: List[Tuple[str, float]], graph: Graph, rng, node_loads) -> str:
        direct = self.next_hop.get((node, dest))
        if direct is not None:
            return direct
        return rng.choice([neighbor for neighbor, _ in neighbors])


def _build_mlp(input_dim: int, hidden_sizes: Tuple[int, ...], output_dim: int):
    torch = _require_torch()
    layers: List[torch.nn.Module] = []
    last = input_dim
    for size in hidden_sizes:
        layers.append(torch.nn.Linear(last, size))
        layers.append(torch.nn.ReLU())
        last = size
    layers.append(torch.nn.Linear(last, output_dim))
    return torch.nn.Sequential(*layers)
