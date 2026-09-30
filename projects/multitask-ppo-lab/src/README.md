# Source layout

The application lives in the `multitask_ppo_lab` package. Run it from the project root with `PYTHONPATH=src`.

## `algorithms/`

| Module | Contents |
|---|---|
| `envs.py` | `NavigationTask` and `KeyDoorTask` gridworlds, BFS distances, `oracle_action`, potential-based shaping |
| `network.py` | `MultiTaskActorCritic`: shared CNN trunk, task embedding, per-task heads, orthogonal initialization |
| `ppo.py` | `PPOConfig`, `gae`, `clipped_policy_loss`, per-task rollouts, and the multi-task `train` loop |
| `evaluation.py` | Held-out episodes, frame recording, and comparison with random and oracle policies |

## `services/`, `api/`, and CLI

| Module | Contents |
|---|---|
| `services/lab_service.py` | Loads the checkpoint, serves curves and evaluation, replays episodes as text frames |
| `api/app.py` | FastAPI factory, `/api/summary`, `/api/episodes`, static console |
| `cli.py` | `train` and `evaluate` commands; saves `policy.pt`, `history.json`, `evaluation.json` |
