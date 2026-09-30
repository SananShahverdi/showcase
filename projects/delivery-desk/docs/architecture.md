# Architecture

## System goal

Give one person a dependable local board for planning delivery work, where an edit is never silently lost and every change can be traced.

## Context

```mermaid
flowchart LR
    user[User] --> ui[Browser console<br/>index.html + app.js]
    ui -->|JSON over HTTP| api[FastAPI app<br/>delivery_desk.api.app]
    api --> db[(SQLite<br/>tasks · events · settings)]
    hub[Portfolio hub] -. mounts .-> api
```

The console is plain HTML, CSS, and a browser module; there is no build step. It detects whether it runs standalone (`/api`) or inside the portfolio hub (`/api/projects/delivery-desk/api`).

## Edit with optimistic concurrency

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Console
    participant API as FastAPI
    participant DB as SQLite
    U->>UI: Save edit
    UI->>API: PATCH /api/tasks/{id} {version, changes}
    API->>DB: BEGIN IMMEDIATE
    API->>DB: SELECT task
    alt version matches
        API->>DB: UPDATE changed fields, version + 1
        API->>DB: INSERT event {field: {from, to}}
        API-->>UI: 200 updated task
    else stale version
        API-->>UI: 409 reload and retry
    end
```

## Data model

| Table | Purpose |
|---|---|
| `tasks` | Current task state with `CHECK` constraints on stage and priority, and a `version` counter |
| `events` | Append-only history: `created` payloads and per-field `{from, to}` changes |
| `settings` | Flags such as `demo_seeded` that keep the sample workspace idempotent |

## Boundaries

Single-user, localhost only. No authentication, notifications, or cloud sync. See [ADR 0001](adr/0001-core-architecture.md).
