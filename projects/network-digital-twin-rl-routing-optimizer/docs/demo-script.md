# Demo script

1. Start the API and console (see the README) or open RouteLab from the portfolio hub. With hub demo data the console opens on a trained six-node mesh.
2. Point at the **Simulation only** label: nothing here touches a real network.
3. **Q-learning run** panel: episodes, seed, mean reward over the last 50 episodes, the reward chart (mean reward per block of episodes), and the policy version with its SHA-256 checksum.
4. **Baseline comparison**: Dijkstra, ECMP, random, and the RL policy on the same seeded trace. Discuss where the tabular policy matches or trails Dijkstra.
5. Click **Fail n0 → n1**: the comparison replays on the changed graph. Click **Recover n0 → n1** to restore it.
6. **Latest decisions** shows per-packet paths and drop reasons.
7. Close with the claim boundary: results are evidence about a model, not a deployment recommendation.
