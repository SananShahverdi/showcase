# Testing strategy

| Layer | Location | What it proves |
|---|---|---|
| Unit | `tests/unit/test_models.py` | Validation contracts: strict whole-unit quantities, SKU pattern, bounds, immutable fields, movement rules |
| Integration | `tests/integration/test_api.py` | Ledger consistency, insufficient-stock rejection, idempotent retries, conflicting request IDs, concurrent dispatches, stale edit rejection, filters, seeding, persistence |
| Browser | `projects/delivery-desk/tests/verify_browser.mjs` | Real workflows in Chromium: item creation, editing, receive and dispatch, rejection of oversized dispatch, ledger filters, low-stock view, mobile layout, persistence across a server restart |

Every test uses a temporary SQLite file through `create_app(db_path=...)`, so tests never touch the user's data.

The concurrency test sends two parallel dispatches of 4 units against 5 in stock and asserts that exactly one succeeds, the balance ends at 1, and only one dispatch reaches the ledger.
