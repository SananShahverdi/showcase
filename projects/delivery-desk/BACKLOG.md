# Product roadmap

## Delivered local product

- [x] Task creation and editing with titles, descriptions, projects, assignees, priorities, and due dates.
- [x] Four-stage board (backlog, in progress, review, done) with moves in either direction.
- [x] Search plus project, stage, and priority filters; priority- and due-date-ordered results.
- [x] Append-only change history recording each field's before and after values.
- [x] Optimistic concurrency: stale edits return 409 instead of overwriting another tab's change.
- [x] Idempotent sample workspace that never clears existing tasks.
- [x] SQLite persistence across restarts, responsive browser console, unit, integration, and browser tests.

## Deployment extensions

- [ ] Add authentication and per-user task ownership before any shared deployment.
- [ ] Add task archiving and deletion with history retention rules.
- [ ] Add a PostgreSQL repository for multi-instance use.
- [ ] Add due-date reminders through an explicit, opt-in notification adapter.
