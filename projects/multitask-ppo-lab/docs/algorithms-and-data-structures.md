# Algorithms and data structures

## Environments

Both tasks are square grids with border walls and random interior walls (15% density), regenerated from a seed at every reset. A layout is accepted only if breadth-first search finds a path, so every episode is solvable. The observation is a 5 × H × W tensor: agent, target (goal or door), walls, key, and a plane that is 1 while the key is carried. Navigation has 4 actions; key-and-door has 6 (4 moves, pick up, open). Every step costs 0.01 and a wall bump costs a further 0.02. Picking up the key pays 0.2, and success pays 1.0. A misplaced pick-up or open only wastes the step: penalizing those actions taught the agent to avoid them before it discovered that the key pays off.

## BFS oracle

Distances to the target are computed once per layout by breadth-first search over free cells. The optimal action is any move that lowers that distance; key-door switches its target from the key to the door after pick-up. The oracle gives both a baseline policy and each layout's optimal step count.

## Potential-based shaping

Training rewards add `F = γΦ(s′) − Φ(s)` with `Φ = −0.05 × remaining optimal steps`. Ng, Harada and Russell (1999) showed that such shaping leaves the set of optimal policies unchanged; the unit test checks the telescoping identity directly. Evaluation always uses the unshaped task reward.

## PPO

Each update collects 128 steps from 32 environments per task with the current policy (8,192 transitions per task), computes GAE(γ = 0.99, λ = 0.95), and runs 4 epochs over 4 minibatches. The loss per task is the clipped surrogate (ε = 0.2) plus 0.5 × value MSE minus an entropy bonus whose coefficient decays linearly from 0.01 to 0.0003; task losses are summed before one optimizer step, with global gradient-norm clipping at 0.5 and linear learning-rate decay from 7e-4.

## Network

Two 3×3 convolutions (32 channels) and a 128-unit layer form the shared trunk. A 16-dimensional learned task embedding is concatenated, followed by a shared 128-unit layer and one policy and one value head per task. Orthogonal initialization uses gain √2 for hidden layers, 0.01 for policy heads, and 1 for value heads.

## Why the original code could not learn

- PPO was trained from a replay buffer of random past transitions. PPO's probability ratio is only valid for data from the current policy, and the discounted returns were computed across shuffled, unrelated transitions.
- The navigation observation showed only the agent, never the goal, so the task was unsolvable from observations; the manipulation task ignored actions entirely.
- The network defined `forward` twice and applied attention to a single token.

Two further problems were found and fixed during the rewrite: default PyTorch initialization collapsed trunk features on sparse one-hot grids, and adding a unit-variance task embedding drowned the state features so every state looked alike. Both are covered in the design notes of `network.py`.
