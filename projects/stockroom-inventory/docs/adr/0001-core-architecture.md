# ADR 0001: Transactional SQLite ledger with idempotent movements

## Status

Accepted.

## Context

Stockroom must run locally with no infrastructure, keep balances correct under retries and concurrent requests, and explain every change in stock.

## Decision

- Store items and movements in one SQLite file; each stock change updates the balance and appends a ledger row in one `BEGIN IMMEDIATE` transaction.
- Enforce non-negative, bounded balances both in application logic and with schema `CHECK` constraints.
- Require a UUID `request_id` per movement, unique in the ledger, so network retries cannot double-apply stock.
- Make SKU and unit immutable; model a different unit as a new SKU.
- Ship the console as static HTML, CSS, and one browser module with no build step.

## Consequences

- Balances and the ledger cannot drift apart, and retries are safe.
- SQLite serializes writers: correct and simple for one user, but a multi-user deployment would need a PostgreSQL repository with row-level locking.
- Corrections are made with new movements rather than edits, which keeps the audit trail complete at the cost of an extra step for the user.
