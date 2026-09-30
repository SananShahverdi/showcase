import numpy as np
import pytest
import torch

from multitask_ppo_lab.algorithms.envs import CHANNELS, KeyDoorTask, NavigationTask, make, oracle_action
from multitask_ppo_lab.algorithms.evaluation import evaluate
from multitask_ppo_lab.algorithms.network import MultiTaskActorCritic
from multitask_ppo_lab.algorithms.ppo import PPOConfig, clipped_policy_loss, gae, train


# --- environments -------------------------------------------------------------

@pytest.mark.parametrize("task", ["navigation", "key_door"])
def test_layouts_are_seeded_solvable_and_observable(task):
    first, second = make(task, seed=11), make(task, seed=11)
    obs = first.reset()
    np.testing.assert_array_equal(obs, second.reset())
    assert obs.shape == (CHANNELS, 7, 7)
    assert obs[0].sum() == 1 and obs[1].sum() == 1          # agent and target are visible
    assert obs[2][0].all() and obs[2][:, -1].all()          # border walls
    assert first.optimal_steps() > 0


@pytest.mark.parametrize("task", ["navigation", "key_door"])
def test_oracle_solves_every_layout_in_exactly_the_optimal_number_of_steps(task):
    for seed in range(50):
        env = make(task, seed=seed)
        env.reset()
        optimal, steps = env.optimal_steps(), 0
        while True:
            result = env.step(oracle_action(env))
            steps += 1
            if result.terminated or result.truncated:
                break
        assert result.info["success"] and steps == optimal


def test_walls_block_movement_and_cost_extra():
    env = NavigationTask(seed=3)
    env.reset()
    env.agent = (1, 1)
    env.walls[0, 1] = True
    result = env.step(0)  # up, into the border
    assert env.agent == (1, 1) and result.info["bumped"]
    assert result.reward == pytest.approx(-0.03)


def test_key_door_requires_the_key_before_opening():
    env = KeyDoorTask(seed=5)
    env.reset()
    env.agent = env.door
    assert env.step(KeyDoorTask.OPEN).reward < 0 and not env.has_key
    env.agent = env.key
    picked = env.step(KeyDoorTask.PICK_UP)
    assert env.has_key and picked.info["event"] == "picked_up"
    assert env.observation()[4].all() and env.observation()[3].sum() == 0
    env.agent = env.door
    opened = env.step(KeyDoorTask.OPEN)
    assert opened.terminated and opened.reward == 1.0


def test_invalid_actions_and_tasks_are_rejected():
    env = make("navigation", seed=1)
    env.reset()
    with pytest.raises(ValueError):
        env.step(4)
    with pytest.raises(ValueError, match="Unknown task"):
        make("flight")


def test_potential_based_shaping_telescopes():
    """The shaping terms along any trajectory sum to gamma^T * phi(s_T) - phi(s_0)."""
    gamma = 0.99
    plain, shaped = make("key_door", seed=8, shaping=0.0), make("key_door", seed=8, shaping=0.05, gamma=gamma)
    plain.reset(), shaped.reset()
    phi0 = -0.05 * shaped.optimal_steps()
    rng = np.random.default_rng(0)
    discounted_bonus, t = 0.0, 0
    for t in range(40):
        action = int(rng.integers(6))
        a, b = plain.step(action), shaped.step(action)
        discounted_bonus += gamma ** t * (b.reward - a.reward)
        if b.terminated:
            break
    phi_end = 0.0 if b.terminated else -0.05 * shaped.optimal_steps()
    assert discounted_bonus == pytest.approx(gamma ** (t + 1) * phi_end - phi0, abs=1e-9)


# --- PPO math -----------------------------------------------------------------

def test_gae_matches_a_hand_calculation_and_resets_at_episode_ends():
    rewards = np.array([[1.0], [0.0], [2.0]], dtype=np.float32)
    values = np.array([[0.5], [0.4], [0.3]], dtype=np.float32)
    dones = np.array([[0.0], [1.0], [0.0]], dtype=np.float32)
    last = np.array([0.2], dtype=np.float32)
    g, lam = 0.9, 0.8
    d2 = 2.0 + g * 0.2 - 0.3
    d1 = 0.0 - 0.4                       # episode ended: no bootstrap
    d0 = 1.0 + g * 0.4 - 0.5
    expected = np.array([d0 + g * lam * d1, d1, d2])
    advantages, returns = gae(rewards, values, dones, last, g, lam)
    np.testing.assert_allclose(advantages[:, 0], expected, rtol=1e-6)
    np.testing.assert_allclose(returns, advantages + values)


def test_clipped_objective_limits_the_update():
    old = torch.log(torch.tensor([0.5, 0.5]))
    new = torch.log(torch.tensor([0.9, 0.1]))  # ratios 1.8 and 0.2
    advantages = torch.tensor([1.0, -1.0])
    # Positive advantage is capped at ratio 1.2; negative advantage at ratio 0.8.
    assert clipped_policy_loss(new, old, advantages, 0.2).item() == pytest.approx(-(1.2 - 0.8) / 2)


def test_network_has_separate_heads_per_task():
    model = MultiTaskActorCritic({"navigation": 4, "key_door": 6}, size=7)
    obs = torch.zeros(3, CHANNELS, 7, 7)
    nav_logits, nav_values = model(obs, "navigation")
    key_logits, _ = model(obs, "key_door")
    assert nav_logits.shape == (3, 4) and key_logits.shape == (3, 6) and nav_values.shape == (3,)


def test_short_training_run_improves_navigation():
    torch.set_num_threads(2)
    config = PPOConfig(tasks=("navigation",), size=5, num_envs=16, rollout_steps=64, updates=25, seed=3)
    model, history = train(config)
    early = np.mean([h.per_task["navigation"]["mean_return"] for h in history[:3]])
    late = np.mean([h.per_task["navigation"]["mean_return"] for h in history[-3:]])
    assert late > early + 0.3
    assert history[-1].per_task["navigation"]["entropy"] < history[0].per_task["navigation"]["entropy"]
    trained = evaluate("ppo_sampled", "navigation", 5, 60, model)
    random = evaluate("random", "navigation", 5, 60)
    assert trained.mean_steps < random.mean_steps
