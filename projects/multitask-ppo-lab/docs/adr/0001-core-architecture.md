# ADR 0001: Honest, from-scratch PPO with held-out evaluation

## Status

Accepted.

## Context

The original "AGI" project combined a PPO agent, an attention network, and two environments, but could not learn: PPO was trained off-policy from a replay buffer, the navigation goal was invisible, and the second environment ignored actions.

## Decision

- Implement PPO from scratch in PyTorch (no RL library) so every step is inspectable and tested.
- Use small, always-solvable gridworlds with visible targets and a BFS oracle, so success and optimality are measurable.
- Train one shared network on both tasks with per-task heads; keep the multi-task idea from the original.
- Use potential-based shaping, which provably preserves optimal policies, and evaluate only on the unshaped reward.
- Train offline and serve a small CPU checkpoint; never train inside an API request.
- Rename the project: "AGI" overstated what a gridworld agent is.

## Consequences

- Results are modest in scale but verifiable against random and optimal baselines on unseen layouts.
- Training takes about half an hour on a laptop CPU; tests use a tiny configuration and stay under a minute.
