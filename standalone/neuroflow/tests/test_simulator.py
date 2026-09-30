import random
from dataclasses import replace

import pytest

from neuroflow.agents import DijkstraRouter, DistanceVectorRouter, QLearningRouter
from neuroflow.analysis import rate_for_bottleneck_load, shortest_distances, shortest_path, shortest_path_loads
from neuroflow.config import Flow, SimConfig
from neuroflow.sim import DiscreteEventSimulator
from neuroflow.topology import Graph, make_grid

LINK = 0.5
LINE = Graph(nodes=["A", "B"], edges={"A": [("B", LINK)], "B": []})
GRID_FLOWS = [Flow("n0_0", "n3_3", 1.0, "A"), Flow("n0_0", "n3_0", 0.8, "B"),
              Flow("n0_3", "n3_3", 0.8, "A"), Flow("n0_3", "n3_0", 1.0, "B")]


def simulate(graph, router, **overrides):
    config = replace(SimConfig(), **overrides)
    return DiscreteEventSimulator(graph, router, config, random.Random(config.seed)).run()


# --- the simulator reproduces queueing theory ---------------------------------

def test_single_mm1_queue_matches_theory():
    lam, mu = 0.5, 1.0
    result = simulate(LINE, DijkstraRouter(LINE), mu=mu, arrival_rate=lam, flows=[Flow("A", "B")],
                      max_packets=40000, warmup_packets=2000)
    expected = 1.0 / (mu - lam) + LINK  # M/M/1 time in system, then the link delay
    assert result.avg_latency == pytest.approx(expected, rel=0.05)
    assert result.max_utilization == pytest.approx(lam / mu, abs=0.02)


def test_single_md1_queue_matches_pollaczek_khinchine():
    lam, mu = 0.5, 1.0
    result = simulate(LINE, DijkstraRouter(LINE), mu=mu, arrival_rate=lam, flows=[Flow("A", "B")],
                      service_dist="deterministic", max_packets=40000, warmup_packets=2000)
    expected = 1.0 / mu + lam / (2 * mu * (mu - lam)) + LINK
    assert result.avg_latency == pytest.approx(expected, rel=0.05)


def test_pareto_interarrivals_keep_the_configured_mean_rate():
    config = SimConfig(arrival_dist="pareto", flows=[Flow("A", "B")], arrival_rate=0.4)
    sim = DiscreteEventSimulator(LINE, DijkstraRouter(LINE), config, random.Random(3))
    samples = [sim._sample_interarrival(0.4, alpha=3.0) for _ in range(200000)]
    assert sum(samples) / len(samples) == pytest.approx(1 / 0.4, rel=0.03)


def test_runs_are_reproducible_for_a_seed():
    first = simulate(LINE, DijkstraRouter(LINE), arrival_rate=0.5, flows=[Flow("A", "B")], max_packets=2000)
    second = simulate(LINE, DijkstraRouter(LINE), arrival_rate=0.5, flows=[Flow("A", "B")], max_packets=2000)
    assert first.latencies == second.latencies


# --- static routing analysis -----------------------------------------------------

def test_shortest_path_loads_and_rate_scaling():
    graph = make_grid(3, 3, jitter=0.0)
    flows = [Flow("n0_0", "n2_2")]
    loads = shortest_path_loads(graph, flows, total_rate=2.0)
    path = shortest_path(graph, "n0_0", "n2_2")
    assert len(path) == 5 and all(loads[node] == 2.0 for node in path[:-1]) and loads["n2_2"] == 0.0
    assert rate_for_bottleneck_load(graph, flows, mu=1.0, load=0.5) == pytest.approx(0.5)


def test_distance_vector_without_queue_term_is_shortest_path():
    graph = make_grid(4, 4)
    dist = shortest_distances(graph)
    dv, sp = DistanceVectorRouter(graph, queue_weight=0.0, mu=1.0), DijkstraRouter(graph)
    for node in graph.nodes:
        for dest in graph.nodes:
            if node != dest:
                choice = dv.select_next_hop(None, node, dest, graph.neighbors(node), graph, random.Random(0), {})
                assert graph.edge_weight(node, choice) + dist[choice][dest] == pytest.approx(dist[node][dest])
                assert choice == sp.next_hop[(node, dest)]


# --- learning behavior -------------------------------------------------------------

def test_q_routing_update_moves_toward_hop_time_plus_best_estimate():
    router = QLearningRouter(alpha=0.5, gamma=1.0, epsilon=0.0)
    state, next_state = ("A", "D", "A", 0, ()), ("B", "D", "A", 0, ())
    router.q[(("B", "D"), "C")] = 4.0
    router.observe_transition(state, "B", cost=2.0, next_state=next_state, next_actions=["C"], terminal=False)
    assert router.q[(("A", "D"), "B")] == pytest.approx(0.5 * (2.0 + 4.0))
    router.observe_transition(state, "B", cost=1.0, next_state=None, next_actions=[], terminal=True)
    assert router.q[(("A", "D"), "B")] == pytest.approx(3.0 + 0.5 * (1.0 - 3.0))


def test_q_routing_matches_shortest_paths_at_light_load():
    graph = make_grid(4, 4)
    rate = rate_for_bottleneck_load(graph, GRID_FLOWS, 1.0, 0.3)
    common = dict(arrival_rate=rate, flows=GRID_FLOWS, max_packets=4000, warmup_packets=3000)
    sp = simulate(graph, DijkstraRouter(graph), **common)
    q = simulate(graph, QLearningRouter(0.2, 1.0, 0.02), **common)
    assert q.avg_latency == pytest.approx(sp.avg_latency, rel=0.12)
    assert q.drop_rate == 0.0


def test_q_routing_beats_shortest_path_near_saturation():
    graph = make_grid(4, 4)
    rate = rate_for_bottleneck_load(graph, GRID_FLOWS, 1.0, 0.9)
    common = dict(arrival_rate=rate, flows=GRID_FLOWS, max_packets=4000, warmup_packets=3000)
    sp = simulate(graph, DijkstraRouter(graph), **common)
    q = simulate(graph, QLearningRouter(0.2, 1.0, 0.02), **common)
    assert q.avg_latency < 0.75 * sp.avg_latency


def test_hop_limit_drops_packets_and_charges_the_router():
    graph = make_grid(4, 4)
    router = QLearningRouter(0.5, 1.0, 0.0)
    result = simulate(graph, router, arrival_rate=0.2, flows=[Flow("n0_0", "n3_3")], max_hops=2,
                      max_packets=200, warmup_packets=0)
    assert result.delivered == 0 and result.drop_rate == 1.0
    assert max(router.q.values()) >= SimConfig().drop_penalty


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        QLearningRouter(0.1, 1.0, 0.0, q_state="everything")
    with pytest.raises(ValueError):
        simulate(LINE, DijkstraRouter(LINE), flows=[])
