# Product roadmap

## Delivered local product

- [x] Item catalog with unique, immutable SKUs and units, categories, shelf locations, and reorder levels.
- [x] Atomic receive and dispatch: the balance update and ledger entry commit in one transaction.
- [x] Insufficient-stock rejection that holds under concurrent dispatches, plus a per-item maximum.
- [x] Idempotent movement requests keyed by UUID, with conflict detection for reused IDs.
- [x] Append-only ledger with before and after balances, filterable by item and kind.
- [x] Low-stock and out-of-stock visibility, search, and category filters.
- [x] Optimistic concurrency on catalog edits, idempotent sample inventory, SQLite persistence, responsive console, unit, integration, and browser tests.

## Deployment extensions

- [ ] Add authentication and role separation between catalog editors and stock handlers.
- [ ] Add stock adjustments (counts, damage, write-offs) as a distinct, audited movement kind.
- [ ] Add reservations for allocated but not yet dispatched stock.
- [ ] Add CSV import and export of the catalog and ledger.
- [ ] Add a PostgreSQL repository for multi-instance use.
