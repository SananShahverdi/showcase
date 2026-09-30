# Architecture

## System goal

Keep an accurate count of stock on hand, where every change is explained by a ledger entry and no sequence of requests can produce a negative balance.

## Context

```mermaid
flowchart LR
    user[User] --> ui[Browser console<br/>index.html + app.js]
    ui -->|JSON over HTTP| api[FastAPI app<br/>stockroom_inventory.api.app]
    api --> db[(SQLite<br/>items · movements · settings)]
    hub[Portfolio hub] -. mounts .-> api
```

The console is plain HTML, CSS, and a browser module with no build step. It detects whether it runs standalone (`/api`) or inside the portfolio hub (`/api/projects/stockroom-inventory/api`).

## Recording a movement

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Console
    participant API as FastAPI
    participant DB as SQLite
    U->>UI: Dispatch 6 units
    UI->>API: POST /api/movements {item_id, kind, quantity, reason, request_id}
    API->>DB: BEGIN IMMEDIATE
    API->>DB: Find movement by request_id
    alt same request already recorded
        API-->>UI: 201 original movement (safe retry)
    else new request
        API->>DB: SELECT item balance
        alt balance would go below zero
            API-->>UI: 409 only N units available
        else
            API->>DB: UPDATE items.quantity
            API->>DB: INSERT movement with balance_before and balance_after
            API-->>UI: 201 movement
        end
    end
```

## Data model

| Table | Purpose |
|---|---|
| `items` | Catalog and current balance; `CHECK (quantity >= 0 AND quantity <= 1000000)`; SKU unique, case-insensitive |
| `movements` | Append-only ledger; `request_id` is `UNIQUE`; `CHECK (balance_after >= 0)` |
| `settings` | Flags such as `demo_seeded` |

## Boundaries

Single-user, localhost only. No purchasing, valuation, reservations, authentication, or cloud sync. See [ADR 0001](adr/0001-core-architecture.md).
