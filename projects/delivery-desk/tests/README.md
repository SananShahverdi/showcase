# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

- `test_models.py`: defaults and trimming, rejection of invalid titles/stages/priorities/dates/unknown fields, required edit versions, null protection, and clearing a due date.

## `integration/`

- `test_api.py`: task lifecycle with history and stale-edit rejection, filters and validation, idempotent seeding, persistence across app instances, and two concurrent edits producing exactly one winner.

## Browser

`verify_browser.mjs` starts an isolated portfolio server with temporary databases and exercises Delivery Desk and Stockroom end to end, including mobile layouts and persistence across a restart. From the portfolio root:

```bash
node projects/delivery-desk/tests/verify_browser.mjs
```
