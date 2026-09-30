"""Compare routing policies across network load.

Load is expressed as the utilization of the busiest node when every flow
follows its shortest path, so 1.0 is the point where static shortest-path
routing saturates. Values above 1.0 are feasible for adaptive routing only if
it spreads traffic over other paths.
"""

import argparse
import csv
import math
import random
from dataclasses import replace
from typing import Callable, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from neuroflow.agents import DQNRouter, DijkstraRouter, DistanceVectorRouter, QLearningRouter  # noqa: E402
from neuroflow.analysis import rate_for_bottleneck_load  # noqa: E402
from neuroflow.config import Flow, SimConfig  # noqa: E402
from neuroflow.sim import DiscreteEventSimulator  # noqa: E402
from neuroflow.topology import make_fishnet, make_grid  # noqa: E402

POLICIES: Dict[str, tuple] = {
    "dijkstra": ("Shortest path", lambda g, cfg, rng: DijkstraRouter(g)),
    "distance-vector": ("Load-aware distance vector", lambda g, cfg, rng: DistanceVectorRouter(g, cfg.queue_weight, cfg.mu)),
    "q_learning": ("Q-routing", lambda g, cfg, rng: QLearningRouter(cfg.alpha, cfg.gamma, cfg.epsilon, cfg.q_state)),
    "dqn": ("DQN routing", lambda g, cfg, rng: DQNRouter(g, cfg, rng)),
}


def build_graph(config: SimConfig):
    if config.topology == "grid":
        return make_grid(config.grid_width, config.grid_height, config.edge_weight, config.edge_jitter, config.seed)
    if config.topology == "fishnet":
        return make_fishnet()
    raise ValueError(f"unknown topology {config.topology}")


def parse_floats(value: str) -> List[float]:
    return [float(item) for item in value.split(",") if item.strip()]


def parse_flows(value: str) -> List[Flow]:
    flows = []
    for item in filter(None, (part.strip() for part in value.split(","))):
        parts = item.split(":")
        if not 2 <= len(parts) <= 4:
            raise ValueError(f"invalid flow '{item}', use src:dst[:weight[:type]]")
        source, dest = parts[0], parts[1]
        weight = float(parts[2]) if len(parts) >= 3 else 1.0
        flow_type = parts[3] if len(parts) == 4 else "A"
        flows.append(Flow(source, dest, weight, flow_type))
    return flows


def parse_flow_class_alphas(value: str) -> Dict[str, float]:
    alphas = {}
    for pair in filter(None, (part.strip() for part in value.split(","))):
        flow_type, alpha = pair.split(":")
        alphas[flow_type] = float(alpha)
    return alphas


def default_flows(config: SimConfig) -> List[Flow]:
    if config.topology == "fishnet":
        return [Flow("S1", "A", 1.0, "A"), Flow("S1", "B", 1.0, "B"), Flow("S2", "B", 1.0, "A"), Flow("S2", "D", 1.0, "B")]
    top_left, top_right = "n0_0", f"n0_{config.grid_width - 1}"
    bottom_left, bottom_right = f"n{config.grid_height - 1}_0", f"n{config.grid_height - 1}_{config.grid_width - 1}"
    return [Flow(top_left, bottom_right, 1.0, "A"), Flow(top_left, bottom_left, 0.8, "B"),
            Flow(top_right, bottom_right, 0.8, "A"), Flow(top_right, bottom_left, 1.0, "B")]


def validate(flows: List[Flow], graph, alphas: Dict[str, float]) -> None:
    nodes = set(graph.nodes)
    for flow in flows:
        if flow.source not in nodes or flow.dest not in nodes:
            raise ValueError(f"flow {flow.source}->{flow.dest} uses a node that is not in the graph")
        if flow.source == flow.dest:
            raise ValueError(f"flow {flow.source}->{flow.dest} must connect different nodes")
        if flow.flow_type not in alphas:
            raise ValueError(f"flow type {flow.flow_type} has no Pareto alpha in --flow-class-alphas")


def run_point(factory: Callable, graph, config: SimConfig, repeats: int) -> Dict[str, float]:
    runs = []
    for rep in range(repeats):
        rng = random.Random(config.seed + rep)
        runs.append(DiscreteEventSimulator(graph, factory(graph, config, rng), config, rng).run())
    means = np.array([run.avg_latency for run in runs])
    ci = 1.96 * means.std(ddof=1) / math.sqrt(repeats) if repeats > 1 else 0.0
    return {
        "mean_latency": float(np.nanmean(means)),
        "ci95": float(ci),
        "p95_latency": float(np.mean([run.p95_latency for run in runs])),
        "drop_rate": float(np.mean([run.drop_rate for run in runs])),
        "mean_hops": float(np.nanmean([run.mean_hops for run in runs])),
        "max_utilization": float(np.mean([run.max_utilization for run in runs])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topology", choices=["grid", "fishnet"], default="grid")
    parser.add_argument("--grid-width", type=int, default=4)
    parser.add_argument("--grid-height", type=int, default=4)
    parser.add_argument("--mu", type=float, default=1.0)
    parser.add_argument("--service-dist", choices=["exponential", "deterministic"], default="exponential")
    parser.add_argument("--loads", type=parse_floats, default=parse_floats("0.3,0.6,0.9,1.1,1.3"),
                        help="Busiest-node utilization under shortest-path routing, e.g. 0.3,0.9,1.3")
    parser.add_argument("--arrival-dist", choices=["exponential", "pareto"], default="exponential")
    parser.add_argument("--pareto-alpha", type=float, default=2.5)
    parser.add_argument("--flow-class-alphas", default="A:3.0,B:1.5")
    parser.add_argument("--flows", default="", help="src:dst[:weight[:type]],... (default: topology flows)")
    parser.add_argument("--agents", default="dijkstra,distance-vector,q_learning")
    parser.add_argument("--max-packets", type=int, default=6000)
    parser.add_argument("--warmup-packets", type=int, default=3000)
    parser.add_argument("--max-sim-time", type=float, default=200000.0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--q-state", choices=["basic", "load"], default="basic")
    parser.add_argument("--queue-weight", type=float, default=1.0)
    parser.add_argument("--plot", default="latency_vs_load.png")
    parser.add_argument("--summary", default="results.csv")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if any(load <= 0 for load in args.loads):
        raise SystemExit("--loads must be positive")
    alphas = parse_flow_class_alphas(args.flow_class_alphas)
    if args.arrival_dist == "pareto" and any(alpha <= 1.0 for alpha in [args.pareto_alpha, *alphas.values()]):
        raise SystemExit("Pareto alphas must be > 1 for a finite mean interarrival time")
    agents = [item.strip() for item in args.agents.split(",") if item.strip()]
    unknown = [agent for agent in agents if agent not in POLICIES]
    if unknown:
        raise SystemExit(f"unknown agents: {', '.join(unknown)}; choose from {', '.join(POLICIES)}")

    config = SimConfig(seed=args.seed, mu=args.mu, service_dist=args.service_dist, arrival_dist=args.arrival_dist,
                       pareto_alpha=args.pareto_alpha, flow_class_alphas=alphas, max_packets=args.max_packets,
                       warmup_packets=args.warmup_packets, max_sim_time=args.max_sim_time, epsilon=args.epsilon,
                       alpha=args.alpha, gamma=args.gamma, q_state=args.q_state, queue_weight=args.queue_weight,
                       topology=args.topology, grid_width=args.grid_width, grid_height=args.grid_height)
    graph = build_graph(config)
    flows = parse_flows(args.flows) if args.flows else default_flows(config)
    validate(flows, graph, alphas)
    config = replace(config, flows=flows)

    rows = []
    for agent in agents:
        label, factory = POLICIES[agent]
        for load in args.loads:
            rate = rate_for_bottleneck_load(graph, flows, config.mu, load)
            point = run_point(factory, graph, replace(config, arrival_rate=rate), args.repeats)
            rows.append({"agent": label, "load": load, "arrival_rate": rate, **point})
            print(f"{label:28s} load {load:4.2f}  W {point['mean_latency']:9.2f} ±{point['ci95']:7.2f}  "
                  f"p95 {point['p95_latency']:9.2f}  drops {point['drop_rate']:.3f}  hops {point['mean_hops']:.2f}", flush=True)

    if args.summary:
        with open(args.summary, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"saved summary to {args.summary}")

    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8))
    for label in dict.fromkeys(row["agent"] for row in rows):
        series = [row for row in rows if row["agent"] == label]
        loads = [row["load"] for row in series]
        left.errorbar(loads, [row["mean_latency"] for row in series], yerr=[row["ci95"] for row in series],
                      marker="o", capsize=3, label=label)
        right.plot(loads, [row["p95_latency"] for row in series], marker="o", label=label)
    for axis, title in ((left, "Mean delivery time (95% CI)"), (right, "95th-percentile delivery time")):
        axis.set_yscale("log")
        axis.axvline(1.0, color="grey", linestyle=":", linewidth=1)
        axis.set_xlabel("Busiest-node utilization under shortest-path routing")
        axis.set_ylabel("Time units")
        axis.set_title(title)
        axis.grid(True, alpha=0.3)
    left.legend()
    fig.suptitle(f"{args.topology} topology, {args.arrival_dist} arrivals, {args.service_dist} service")
    fig.tight_layout()
    fig.savefig(args.plot, dpi=130, metadata={"Software": None})
    print(f"saved plot to {args.plot}")


if __name__ == "__main__":
    main()
