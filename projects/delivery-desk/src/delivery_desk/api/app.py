"""Local task board with atomic history and optimistic edit protection."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT = Path(__file__).resolve().parents[3]
Status = Literal["backlog", "in_progress", "review", "done"]
Priority = Literal["low", "medium", "high"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
 project TEXT NOT NULL, assignee TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL CHECK(status IN ('backlog','in_progress','review','done')),
 priority TEXT NOT NULL CHECK(priority IN ('low','medium','high')),
 due_date TEXT, version INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL REFERENCES tasks(id),
 action TEXT NOT NULL, changes TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class TaskFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    project: str = Field(default="General", min_length=1, max_length=80)
    assignee: str = Field(default="", max_length=80)
    status: Status = "backlog"
    priority: Priority = "medium"
    due_date: date | None = None


class TaskEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    project: str | None = Field(default=None, min_length=1, max_length=80)
    assignee: str | None = Field(default=None, max_length=80)
    status: Status | None = None
    priority: Priority | None = None
    due_date: date | None = None

    @field_validator("title", "description", "project", "assignee", "status", "priority")
    @classmethod
    def prevent_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Delivery Desk", version="1.0.0")
    app.state.db_path = str(db_path or os.getenv("DELIVERY_DESK_DB") or PROJECT / ".local/data/delivery.sqlite3")

    @contextmanager
    def database():
        path = Path(app.state.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.executescript(SCHEMA)
            with connection:
                yield connection
        finally:
            connection.close()

    def add_task(connection, payload: dict) -> dict:
        stamp = now()
        fields = list(payload)
        cursor = connection.execute(
            f"INSERT INTO tasks ({','.join(fields)},created_at,updated_at) VALUES ({','.join('?' for _ in fields)},?,?)",
            [*payload.values(), stamp, stamp],
        )
        task = dict(connection.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone())
        connection.execute("INSERT INTO events(task_id,action,changes,created_at) VALUES(?,?,?,?)",
                           (task["id"], "created", json.dumps(payload), stamp))
        return task

    @app.get("/health")
    def health():
        with database() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "storage": "sqlite"}

    @app.get("/api/tasks")
    def tasks(q: str = Query(default="", max_length=200), project: str | None = None,
              status: Status | None = None, priority: Priority | None = None):
        clauses, values = [], []
        if q.strip():
            clauses.append("(instr(lower(title),lower(?)) > 0 OR instr(lower(description),lower(?)) > 0 OR instr(lower(assignee),lower(?)) > 0)")
            values.extend([q.strip()] * 3)
        for key, value in (("project", project), ("status", status), ("priority", priority)):
            if value:
                clauses.append(f"{key} = ?")
                values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database() as connection:
            rows = connection.execute("SELECT * FROM tasks" + where + " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, due_date IS NULL, due_date, id DESC", values)
            items = [dict(row) for row in rows]
            projects = [row[0] for row in connection.execute("SELECT DISTINCT project FROM tasks ORDER BY project COLLATE NOCASE")]
            counts = dict(connection.execute("SELECT status, count(*) FROM tasks GROUP BY status").fetchall())
        return {"items": items, "projects": projects, "counts": {key: counts.get(key, 0) for key in ("backlog", "in_progress", "review", "done")}}

    @app.post("/api/tasks", status_code=201)
    def create_task(payload: TaskFields):
        with database() as connection:
            return add_task(connection, payload.model_dump(mode="json"))

    @app.get("/api/tasks/{task_id}")
    def task_detail(task_id: int):
        with database() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Task not found")
            events = [dict(event) for event in connection.execute("SELECT * FROM events WHERE task_id = ? ORDER BY id DESC", (task_id,))]
            for event in events:
                event["changes"] = json.loads(event["changes"])
            return {**dict(row), "history": events}

    @app.patch("/api/tasks/{task_id}")
    def update_task(task_id: int, payload: TaskEdit):
        updates = payload.model_dump(exclude_unset=True, mode="json")
        version = updates.pop("version")
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Task not found")
            if row["version"] != version:
                raise HTTPException(409, "This task changed in another tab. Close the editor and open it again to load the latest version.")
            changes = {key: {"from": row[key], "to": value} for key, value in updates.items() if row[key] != value}
            if changes:
                stamp = now()
                fields = list(changes)
                connection.execute(f"UPDATE tasks SET {','.join(key + ' = ?' for key in fields)}, version = version + 1, updated_at = ? WHERE id = ?",
                                   [*[updates[key] for key in fields], stamp, task_id])
                connection.execute("INSERT INTO events(task_id,action,changes,created_at) VALUES(?,?,?,?)", (task_id, "updated", json.dumps(changes), stamp))
            return dict(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

    @app.post("/api/demo/seed")
    def seed():
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM settings WHERE key = 'demo_seeded'").fetchone():
                return {"added": 0, "message": "Sample workspace has already been added."}
            today = date.today()
            samples = [
                ("Map the customer onboarding flow", "Write the happy path and the three most common recovery paths.", "Customer portal", "Aylin", "backlog", "medium", 5),
                ("Add invoice search and export", "Filter by month and customer. Export the current results as CSV.", "Customer portal", "Sanan", "in_progress", "high", 2),
                ("Review accessible form errors", "Check keyboard focus, labels, and error announcements with a screen reader.", "Customer portal", "Leyla", "review", "high", 1),
                ("Document the local setup", "A clean checkout should run with the documented commands.", "Internal tools", "Sanan", "done", "medium", -1),
                ("Investigate slow audit queries", "Compare query plans on 10,000 events and add an index if required.", "Internal tools", "Aylin", "in_progress", "high", -2),
                ("Collect feedback from operations", "Schedule a short walkthrough and record the top three friction points.", "Internal tools", "", "backlog", "low", 7),
            ]
            for title, description, project, assignee, status, priority, days in samples:
                add_task(connection, dict(title=title, description=description, project=project, assignee=assignee,
                                          status=status, priority=priority, due_date=(today + timedelta(days=days)).isoformat()))
            connection.execute("INSERT INTO settings VALUES('demo_seeded','1')")
            return {"added": len(samples), "message": "Six sample tasks added. Your existing tasks are unchanged."}

    frontend = PROJECT / "frontend"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
