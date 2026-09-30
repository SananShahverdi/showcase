# Algorithms and data structures

| Algorithm | Where | Notes |
|---|---|---|
| Weighted Dijkstra | `baselines.py` (networkx `shortest_path`) | Edge weight is the current effective latency. |
| Seeded ECMP | `baselines.py` | Random choice among all equal-cost shortest paths using the evaluation's seeded RNG. |
| Seeded random routing | `baselines.py` | Random simple path with a hop cutoff of 8. |
| Tabular Q-learning | `q_learning.py` | Reward: +100 on delivery, minus hop latency, minus 25 for revisiting a node. Learning rate 0.25, discount 0.9, epsilon from 1.0 to 0.05 over 80% of episodes. |
| Fair comparison | `inference_service.py` | Runtime state is reset before each algorithm and the same seeded traffic trace is replayed. |
| p95 latency | `inference_service.py` | Nearest-rank percentile over delivered packets. |

## Data structures

| Structure | Purpose |
|---|---|
| `networkx.DiGraph` | Active topology; failed links are removed from the graph and kept in `NetworkState.links`. |
| `NetworkState` (`nodes`, `links`, `packets`, `time_step`) | Serializable simulator state returned by `GET /api/simulator/state`. |
| Q-table `dict[(current, target, action)] → float` | Policy; serialized in sorted order and hashed with SHA-256 to derive the policy version. |
| `TrainingResult` | Policy version, episodes, seed, mean reward over the last 50 episodes, checksum, full reward curve. |
| `SimulationMetrics` | Per-algorithm evaluation result. |

## Complexity

Training is O(episodes × 2·nodes × out-degree). Each evaluation is O(packets × path cost), where Dijkstra is O(E log V) and the random baseline enumerates simple paths, which grows quickly on dense graphs; that is why the hop cutoff exists.
