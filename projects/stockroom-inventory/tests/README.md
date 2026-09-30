# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

- `test_models.py`: defaults, whole-unit (strict integer) quantities, unsafe SKU rejection, stock bounds, immutable SKU/unit/quantity on edit, and movement validation with generated request IDs.

## `integration/`

- `test_api.py`: receive/dispatch ledger consistency, insufficient-stock rejection, idempotent retries and conflicting request IDs, concurrent dispatches, catalog edits and stale versions, filters, idempotent seeding, and persistence.

## Browser

Stockroom's browser workflows run in the shared business-apps script, `projects/delivery-desk/tests/verify_browser.mjs`. From the portfolio root:

```bash
node projects/delivery-desk/tests/verify_browser.mjs
```
