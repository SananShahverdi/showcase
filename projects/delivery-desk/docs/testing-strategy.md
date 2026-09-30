# Testing strategy

| Layer | Location | What it proves |
|---|---|---|
| Unit | `tests/unit/test_models.py` | Validation contracts: defaults, trimming, enum limits, forbidden unknown fields, null protection |
| Integration | `tests/integration/test_api.py` | Full HTTP lifecycle, history content, 409 on stale edits, filters, idempotent seeding, persistence across app instances, concurrent-edit safety |
| Browser | `tests/verify_browser.mjs` | Real user workflows in Chromium: creation, editing, stage moves, search and filters, error recovery, mobile layout, keyboard dismissal, persistence across a server restart |

Every test uses a temporary SQLite file through `create_app(db_path=...)`, so tests never touch the user's data.

The concurrency test fires two edits carrying the same version from separate threads and asserts the results are exactly one 200 and one 409.
