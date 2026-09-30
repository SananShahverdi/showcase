from network_digital_twin_rl_routing_optimizer.algorithms.simulator import NetworkSimulator
from network_digital_twin_rl_routing_optimizer.domain.models import TopologyType, RoutingAlgorithm
from network_digital_twin_rl_routing_optimizer.algorithms.baselines import RoutingLogic
from network_digital_twin_rl_routing_optimizer.algorithms.q_learning import QLearningRouter

def test_simulator_builds_topologies():
    sim = NetworkSimulator()
    
    sim.build_topology(TopologyType.RING, 5)
    assert len(sim.get_active_graph().nodes) == 5
    assert len(sim.get_active_graph().edges) == 10 # Bidirectional ring
    
    sim.build_topology(TopologyType.STAR, 5)
    assert len(sim.get_active_graph().nodes) == 5
    assert len(sim.get_active_graph().edges) == 8 # 4 spokes bidirectional

def test_baselines():
    sim = NetworkSimulator()
    sim.build_topology(TopologyType.RING, 5)
    graph = sim.get_active_graph()
    
    path_dijkstra = RoutingLogic.get_path(RoutingAlgorithm.DIJKSTRA, graph, "n0", "n2")
    assert path_dijkstra is not None
    assert path_dijkstra[0] == "n0"
    assert path_dijkstra[-1] == "n2"
    
    path_random = RoutingLogic.get_path(RoutingAlgorithm.RANDOM, graph, "n0", "n2")
    assert path_random is not None
    
    path_ecmp = RoutingLogic.get_path(RoutingAlgorithm.ECMP, graph, "n0", "n2")
    assert path_ecmp is not None

    # RL is not an alias for shortest path: it requires a separately trained policy.
    assert RoutingLogic.get_path(RoutingAlgorithm.RL_AGENT, graph, "n0", "n2") is None

def test_link_failure():
    sim = NetworkSimulator()
    sim.build_topology(TopologyType.RING, 3) # n0, n1, n2
    graph = sim.get_active_graph()
    
    assert graph.has_edge("n0", "n1")
    sim.fail_link("n0", "n1")
    
    graph2 = sim.get_active_graph()
    assert not graph2.has_edge("n0", "n1")
    sim.recover_link("n0", "n1")
    assert sim.get_active_graph().has_edge("n0", "n1")


def test_q_learning_trains_a_versioned_policy():
    sim = NetworkSimulator()
    sim.build_topology(TopologyType.MESH, 5)
    policy = QLearningRouter()
    result = policy.train(sim.get_active_graph(), episodes=300, seed=9)
    path = policy.get_path(sim.get_active_graph(), "n0", "n4")
    assert result.policy_version.startswith("q-")
    assert len(result.checksum) == 64
    assert path == ["n0", "n4"]


def test_capacity_delay_and_runtime_reset():
    import random
    sim = NetworkSimulator()
    sim.build_topology(TopologyType.RING, 4)
    delivered, latency, reason = sim.apply_path(["n0", "n1"], 20, random.Random(1))
    assert delivered and reason is None and latency > 10
    assert sim.state.links[0].current_load >= 0
    sim.reset_runtime()
    assert all(link.current_load == 0 for link in sim.state.links)
