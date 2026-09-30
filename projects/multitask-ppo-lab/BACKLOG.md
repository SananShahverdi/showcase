# Product roadmap

## Delivered

- [x] Seeded, always-solvable navigation and key-and-door gridworlds with a shared five-channel observation.
- [x] Breadth-first-search oracle for optimal actions and optimal step counts.
- [x] Potential-based reward shaping with a test that it telescopes (policy-invariant).
- [x] PPO from scratch: on-policy rollouts, GAE(λ), clipped objective, value loss, entropy bonus, gradient clipping, learning-rate annealing.
- [x] One shared network with a concatenated task embedding and per-task policy and value heads.
- [x] Held-out evaluation against random and optimal play; greedy and sampled PPO reported separately.
- [x] Pretrained checkpoint, CLI, API, replay console, unit, integration, and browser tests.
- [x] Bootstrap from the value of the final state on time-limit truncation instead of treating it as terminal.
- [x] Entropy-bonus annealing, and a key-and-door reward without the misuse penalty that trapped exploration.

## Research extensions

- [ ] Compare against single-task agents trained with the same budget to measure transfer between tasks.
- [ ] Larger grids with a curriculum, and recurrent policies for partial observability.
- [ ] Vectorize environment stepping in NumPy to raise throughput beyond ~1,300 steps per second.
