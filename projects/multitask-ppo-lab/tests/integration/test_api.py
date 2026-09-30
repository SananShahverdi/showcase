import json

import pytest
import torch
from fastapi.testclient import TestClient

from multitask_ppo_lab.algorithms.evaluation import compare
from multitask_ppo_lab.algorithms.ppo import PPOConfig, train
from multitask_ppo_lab.api.app import create_app
from multitask_ppo_lab.cli import load, save
from multitask_ppo_lab.services.lab_service import LabService


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    torch.set_num_threads(2)
    out = tmp_path_factory.mktemp("artifacts")
    config = PPOConfig(size=5, num_envs=4, rollout_steps=32, updates=2, seed=1)
    model, history = train(config)
    save(model, config, history, out)
    (out / "evaluation.json").write_text(json.dumps(compare(model, model.tasks, config.size, episodes=3)))
    return out


@pytest.fixture(scope="module")
def client(artifacts):
    with TestClient(create_app(LabService(artifacts))) as test_client:
        yield test_client


def test_checkpoint_round_trips(artifacts):
    model, training = load(artifacts)
    assert model.tasks == ["navigation", "key_door"] and training["size"] == 5


def test_summary_exposes_curves_and_evaluation(client):
    body = client.get("/api/summary").json()
    assert set(body["curves"]) == {"navigation", "key_door"}
    assert len(body["curves"]["navigation"]) == 2
    assert {row["policy"] for row in body["evaluation"]} == {"random", "ppo_sampled", "ppo_greedy", "oracle"}
    assert body["tasks"]["key_door"]["actions"][-2:] == ["pick up", "open"]
    assert body["env_steps"] == 2 * 4 * 32 * 2  # updates × environments × rollout steps × tasks
    assert body["training_seconds"] > 0
    assert client.get("/health").json()["policy_loaded"] is True


def test_episode_replay_is_deterministic_and_oracle_is_optimal(client):
    request = {"task": "key_door", "policy": "oracle", "seed": 4}
    first, second = client.post("/api/episodes", json=request).json(), client.post("/api/episodes", json=request).json()
    assert first == second
    assert first["success"] and first["steps"] == first["optimal_steps"]
    assert len(first["frames"]) == first["steps"] + 1 == len(first["actions"]) + 1
    assert first["frames"][0]["rows"][0] == "#####"
    assert first["frames"][-1]["has_key"] is True


def test_invalid_requests_are_rejected(client):
    assert client.post("/api/episodes", json={"task": "flight"}).status_code == 422
    assert client.post("/api/episodes", json={"task": "navigation", "policy": "cheat"}).status_code == 422


def test_missing_checkpoint_is_reported_clearly(tmp_path):
    with TestClient(create_app(LabService(tmp_path))) as empty:
        response = empty.get("/api/summary")
        assert response.status_code == 503 and "cli train" in response.json()["detail"]
        assert empty.get("/health").json()["policy_loaded"] is False


def test_readme_results_match_bundled_artifacts():
    """The published results table must be regenerated whenever the checkpoint changes."""
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("render_results", root / "scripts/render_results.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not (root / "artifacts/policy.pt").exists():
        pytest.skip("no bundled checkpoint")
    assert module.readme_section((root / "README.md").read_text()) == module.render(), "run scripts/render_results.py"
