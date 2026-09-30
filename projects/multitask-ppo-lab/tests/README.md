# Tests

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/test_algorithms.py`

Seeded and solvable layouts with visible targets; the oracle solves 50 layouts per task in exactly the optimal number of steps; wall bumps; key-door rules; invalid input; **potential-based shaping telescopes to γᵀΦ(s_T) − Φ(s₀)**; GAE against a hand calculation including an episode boundary; the clipped objective's limits; separate heads; and a short seeded training run whose returns rise, entropy falls, and which beats a random agent.

## `integration/test_api.py`

Trains a tiny checkpoint in a temporary folder, then checks checkpoint round-trips, the summary endpoint, deterministic replays where the oracle is optimal, input validation, and a clear error when no checkpoint exists.

## Browser

`verify_browser.mjs` drives the console through the portfolio hub (`npm run test:ppo` from the portfolio root).
