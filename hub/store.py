"""Small durable store for this single-user local workspace."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS saved_projects (
                    slug TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def saved(self):
        with self.connect() as db:
            return [row["slug"] for row in db.execute("SELECT slug FROM saved_projects ORDER BY created_at DESC")]

    def save(self, slug: str, enabled: bool):
        with self.connect() as db:
            if enabled:
                db.execute("INSERT OR IGNORE INTO saved_projects(slug) VALUES (?)", (slug,))
            else:
                db.execute("DELETE FROM saved_projects WHERE slug = ?", (slug,))

    def add_note(self, name, email, message):
        with self.connect() as db:
            cursor = db.execute("INSERT INTO notes(name,email,message) VALUES (?,?,?)", (name, email, message))
            return dict(db.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def notes(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM notes ORDER BY id DESC LIMIT 200")]
