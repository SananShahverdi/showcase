# NeuroFlow

A discrete-event network simulator that tests whether routers that learn from delay can beat static shortest-path routing as a network approaches congestion. It models every node as a single-server queue, sends packets along learned or computed routes, and measures delivery time, tail latency, drops, and path length.

![Mean and 95th-percentile delivery time against load](docs/latency_vs_load.png)

## Result

On a 4 × 4 grid with four crossing flows and exponential service (3 seeded runs per point, 3,000 warm-up and 6,000 measured packets):

<!-- results:start -->
| Busiest-node load | Shortest path | Load-aware distance vector | Q-routing |
|---:|---:|---:|---:|
| 30% | 10.4 ± 0.1 (4.7 hops) | 10.1 ± 0.0 (4.8 hops) | 10.4 ± 0.1 (4.8 hops) |
| 60% | 13.4 ± 0.4 (4.7 hops) | 11.7 ± 0.1 (4.9 hops) | 13.3 ± 2.0 (5.0 hops) |
| 90% | 28.1 ± 4.8 (4.6 hops) | 14.4 ± 0.2 (5.2 hops) | 19.0 ± 2.4 (5.0 hops) |
| 110% | 408.0 ± 75.4 (4.6 hops) | 18.4 ± 0.9 (5.5 hops) | 31.7 ± 14.9 (5.2 hops) |
| 130% | 846.6 ± 22.5 (4.6 hops) | 1273.5 ± 1517.5 (9.6 hops) | 167.8 ± 23.5 (5.4 hops) |

Mean delivery time in time units with its 95% confidence interval, and mean hops per packet. One time unit is the mean service time (μ = 1); link delays are about 1.
<!-- results:end -->

- **Light load:** every policy performs about the same, and learned routing converges to shortest paths.
- **Near and just past saturation:** static routing collapses once its bottleneck is overloaded (408 time units at 110%). The load-aware distance vector is the best policy here, halving delay at 90% and staying at 18 at 110%; Q-routing is second, at 19 and 32.
- **Heavy overload (130%):** the load-aware distance vector becomes unstable. Packets chase momentarily short queues, path length doubles, and results swing widely between runs (1,274 ± 1,518), which is the route oscillation that load-sensitive distance-vector routing is known for. Q-routing, which reacts to smoothed measured delays rather than instantaneous queues, is the only policy that stays usable (168, against 847 for shortest paths).

## Policies

| Policy | Decision |
|---|---|
| Shortest path | Static Dijkstra routes on link delays |
| Load-aware distance vector | Converged Bellman-Ford distance to the destination, plus each neighbor's current queue in service-time units |
| Q-routing (Boyan and Littman, 1994) | Learns Q(node, destination, next hop), the expected time to deliver, from the measured duration of every hop |
| DQN routing (optional) | Neural approximation of the same Q-values from node, destination, flow class, and queue occupancy |

## Model

- **Nodes:** FIFO single-server queues with exponential (M/M/1) or deterministic (M/D/1) service at rate μ; optional finite buffers.
- **Links:** directed, with fixed propagation delay; grid (with seeded delay jitter) and a small "fishnet" topology.
- **Traffic:** weighted source-destination flows with Poisson or heavy-tailed Pareto arrivals, and a per-class Pareto shape.
- **Load axis:** the utilization of the busiest node when every flow follows its shortest path. At 1.0 static routing saturates; beyond it, only routing that uses other paths can stay stable.
- **Safety:** packets exceeding a hop limit (4 × number of nodes) are dropped and counted, and learning routers are charged a penalty for them.

## Verification

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The 11 tests check that a single queue reproduces the M/M/1 time in system 1/(μ − λ) and the Pollaczek-Khinchine M/D/1 formula within 5%, that Pareto interarrivals keep the configured rate, that distance-vector routing without a queue term equals shortest-path routing everywhere, that the Q-routing update is exact, that Q-routing matches shortest paths at light load and beats them near saturation, and that hop limits drop and penalize looping packets.

## Run experiments

```bash
python run_experiment.py                                   # grid, default loads 0.3-1.3
python run_experiment.py --topology fishnet --loads 0.5,0.9,1.2
python run_experiment.py --arrival-dist pareto --flow-class-alphas A:3.0,B:1.5
python run_experiment.py --service-dist deterministic --repeats 5
python run_experiment.py --agents dijkstra,q_learning,dqn  # DQN needs requirements-dqn.txt
```

Each run prints one line per policy and load, writes `results.csv`, and saves a two-panel plot. `--flows "src:dst[:weight[:type]],..."` overrides the default traffic, and `--q-state load` adds queue occupancy to the Q-routing state.

## Layout

```text
neuroflow/sim.py        event loop, queues, hop timing, drops, measurements
neuroflow/agents.py     shortest path, distance vector, Q-routing, DQN
neuroflow/analysis.py   shortest distances, next hops, per-node shortest-path load
neuroflow/topology.py   grid and fishnet graphs
run_experiment.py       load sweep, repeated runs, CSV and plot
tests/                  queueing-theory and routing-behavior checks
```
