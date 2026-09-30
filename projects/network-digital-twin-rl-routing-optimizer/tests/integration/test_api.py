from fastapi.testclient import TestClient

from network_digital_twin_rl_routing_optimizer.api.app import app

client = TestClient(app)


def test_train_compare_and_failure_replay():
    topology = client.post("/api/simulator/topology", json={"topology": "mesh", "num_nodes": 6})
    assert topology.status_code == 200
    untrained = client.post("/api/evaluate", json={"algorithm": "rl_agent", "num_packets": 20, "seed": 17})
    assert untrained.status_code == 409

    training = client.post("/api/train", json={"episodes": 400, "seed": 17})
    assert training.status_code == 200
    policy_version = training.json()["policy_version"]
    assert policy_version.startswith("q-")

    request = {"algorithms": ["dijkstra", "ecmp", "random", "rl_agent"], "num_packets": 60, "seed": 17}
    first = client.post("/api/compare", json=request)
    second = client.post("/api/compare", json=request)
    assert first.status_code == second.status_code == 200
    assert first.json()["results"] == second.json()["results"]
    for metrics in first.json()["results"].values():
        assert metrics["delivered_packets"] + metrics["dropped_packets"] == 60
    assert first.json()["results"]["rl_agent"]["policy_version"] == policy_version

    assert client.post("/api/simulator/fail", json={"source": "n0", "target": "n1"}).status_code == 200
    assert not any(link["source"] == "n0" and link["target"] == "n1" and link["is_active"] for link in client.get("/api/simulator/state").json()["links"])
    assert client.post("/api/simulator/recover", json={"source": "n0", "target": "n1"}).status_code == 200
    experiments = client.get("/api/dashboard/experiments").json()
    assert any(item["kind"] == "training" for item in experiments)
    assert any(item["kind"] == "evaluation" for item in experiments)


def test_latest_results_follow_the_current_policy():
    client.post("/api/simulator/topology", json={"topology": "ring", "num_nodes": 5})
    assert client.get("/api/lab/latest").json() == {"training": None, "comparison": None}

    seeded = client.post("/api/demo/seed").json()
    latest = client.get("/api/lab/latest").json()
    assert latest["training"]["policy_version"] == seeded["training"]["policy_version"]
    assert latest["training"]["reward_curve"] == seeded["training"]["reward_curve"]
    assert latest["comparison"] == seeded["comparison"]

    # Retraining invalidates the comparison made with the previous policy.
    retrained = client.post("/api/train", json={"episodes": 100, "seed": 3}).json()
    latest = client.get("/api/lab/latest").json()
    assert latest["training"]["policy_version"] == retrained["policy_version"]
    assert latest["comparison"] is None

    # Rebuilding the topology discards the policy and its results.
    client.post("/api/simulator/topology", json={"topology": "mesh", "num_nodes": 4})
    assert client.get("/api/lab/latest").json() == {"training": None, "comparison": None}
