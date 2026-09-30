# ADR 0001: SQLite with optimistic concurrency and a build-free console

## Status

Accepted.

## Context

Delivery Desk must run locally with no infrastructure, survive restarts, and protect against two browser tabs overwriting each other.

## Decision

- Store data in a single SQLite file, opened per request, with writes in one transaction.
- Use an integer `version` per task and reject stale writes with HTTP 409.
- Record history as per-field diffs in an append-only `events` table.
- Ship the console as static HTML, CSS, and one browser module with no build step.

## Consequences

- Zero setup and durable local storage; the database is a single portable file.
- SQLite serializes writers, which is ideal for one user but not for a busy multi-user service; a PostgreSQL repository would be required for that.
- Users occasionally see a 409 and must reload, which is preferable to silent data loss.
