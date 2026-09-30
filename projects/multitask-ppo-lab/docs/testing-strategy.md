# Testing strategy

| Layer | What it proves |
|---|---|
| Environment tests | Layouts are seeded and solvable, targets are visible, rules behave, and the BFS oracle is exactly optimal on 100 layouts |
| Math tests | GAE matches a hand calculation, the clipped objective caps updates, and shaping telescopes (so it cannot change optimal policies) |
| Learning test | A 25-update seeded run raises returns, lowers entropy, and beats a random agent, which catches silent learning failures like the ones found during the rewrite |
| API tests | A tiny trained checkpoint round-trips, replays are deterministic, and missing checkpoints produce a clear 503 |
| Browser test | The console loads curves and evaluation, animates three agents, switches tasks, and fits a phone screen |
