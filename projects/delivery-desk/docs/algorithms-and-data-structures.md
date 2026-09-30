# Algorithms and data structures

## Optimistic concurrency control

Each task carries an integer `version`. A client must send the version it last read. The update runs in a `BEGIN IMMEDIATE` transaction, which takes SQLite's reserved lock before reading, so the compare and the write are atomic. A mismatch returns HTTP 409 and nothing is written. Only fields whose values actually changed are written; a no-op edit does not bump the version or add history.

## Change history as a diff log

Instead of storing full snapshots, each update stores a map of `field -> {from, to}`. This keeps history compact and directly answers "who changed what". Creation stores the full initial payload. History is read newest first by primary key.

## Filtering and ordering

Search uses `instr(lower(column), lower(?))` across title, description, and assignee. Unlike `LIKE`, `instr` has no wildcard characters, so user input such as `%` or `_` is matched literally. Results are ordered by priority rank (high, medium, low), then by due date with undated tasks last, then newest first.

## Idempotent seeding

The sample workspace inserts six tasks and records a `demo_seeded` flag in the same transaction. Repeated calls return `added: 0` and never modify existing tasks.

## Complexity

With the small, local data volumes this app targets, list queries are full scans (`O(n)`) and single-task reads use the primary key (`O(log n)`). An index on `(status, priority, due_date)` would be the first addition if the board grew to many thousands of tasks.
