# Architecture

```mermaid
flowchart LR
    subgraph Training [CLI training, offline]
        R1[Navigation rollouts] --> G[GAE]
        R2[Key-door rollouts] --> G
        G --> L[Summed clipped PPO losses]
        L --> N[MultiTaskActorCritic]
        N --> R1
        N --> R2
        N --> A[(artifacts: policy.pt, history.json, evaluation.json)]
    end
    A --> S[LabService]
    S --> API[FastAPI /api/summary, /api/episodes]
    API --> UI[Replay console]
```

Training happens offline through the CLI and writes a small checkpoint. The API only loads it and runs inference on CPU, so the console responds instantly and never trains in a request.

```mermaid
sequenceDiagram
    participant UI as Console
    participant API as FastAPI
    participant S as LabService
    UI->>API: POST /api/episodes {task, policy, seed}
    API->>S: episode()
    S->>S: build held-out layout (seed + 1,000,000)
    loop until success or step limit
        S->>S: policy chooses action, env steps, record frame
    end
    S-->>UI: frames, actions, steps, optimal_steps
```
