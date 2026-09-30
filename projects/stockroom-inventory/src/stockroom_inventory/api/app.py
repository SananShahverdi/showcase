"""Inventory with transactional balances and an append-only movement ledger."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT = Path(__file__).resolve().parents[3]
MAX_STOCK = 1_000_000
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
 id INTEGER PRIMARY KEY, sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
 name TEXT NOT NULL, category TEXT NOT NULL, location TEXT NOT NULL,
 unit TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity >= 0 AND quantity <= 1000000),
 reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0),
 version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS movements (
 id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id),
 kind TEXT NOT NULL CHECK(kind IN ('receive','dispatch')),
 quantity INTEGER NOT NULL CHECK(quantity > 0),
 balance_before INTEGER NOT NULL, balance_after INTEGER NOT NULL CHECK(balance_after >= 0),
 reason TEXT NOT NULL, reference TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS movements_item ON movements(item_id, id DESC);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sku: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="General", min_length=1, max_length=60)
    location: str = Field(default="Unassigned", min_length=1, max_length=60)
    unit: str = Field(default="units", min_length=1, max_length=20)
    quantity: int = Field(default=0, ge=0, le=MAX_STOCK, strict=True)
    reorder_level: int = Field(default=5, ge=0, le=MAX_STOCK, strict=True)


class ItemEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    location: str | None = Field(default=None, min_length=1, max_length=60)
    reorder_level: int | None = Field(default=None, ge=0, le=MAX_STOCK, strict=True)

    @field_validator("name", "category", "location", "reorder_level")
    @classmethod
    def prevent_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class MovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    item_id: int = Field(ge=1)
    kind: Literal["receive", "dispatch"]
    quantity: int = Field(ge=1, le=MAX_STOCK, strict=True)
    reason: str = Field(min_length=3, max_length=300)
    reference: str = Field(default="", max_length=80)
    request_id: UUID = Field(default_factory=uuid4)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Stockroom Inventory", version="1.0.0")
    app.state.db_path = str(db_path or os.getenv("STOCKROOM_INVENTORY_DB") or PROJECT / ".local/data/inventory.sqlite3")

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

    def add_item(connection, payload: dict) -> dict:
        stamp = now()
        payload["sku"] = payload["sku"].upper()
        fields = list(payload)
        cursor = connection.execute(f"INSERT INTO items ({','.join(fields)},created_at,updated_at) VALUES ({','.join('?' for _ in fields)},?,?)", [*payload.values(), stamp, stamp])
        item = dict(connection.execute("SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)).fetchone())
        if item["quantity"]:
            connection.execute("INSERT INTO movements(item_id,kind,quantity,balance_before,balance_after,reason,reference,request_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                               (item["id"], "receive", item["quantity"], 0, item["quantity"], "Opening stock", "", str(uuid4()), stamp))
        return item

    @app.get("/health")
    def health():
        with database() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "storage": "sqlite"}

    @app.get("/api/items")
    def list_items(q: str = Query(default="", max_length=200), category: str | None = None, low_stock: bool = False):
        clauses, values = [], []
        if q.strip():
            clauses.append("(instr(lower(sku),lower(?)) > 0 OR instr(lower(name),lower(?)) > 0 OR instr(lower(location),lower(?)) > 0)")
            values.extend([q.strip()] * 3)
        if category:
            clauses.append("category = ?")
            values.append(category)
        if low_stock:
            clauses.append("quantity <= reorder_level")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database() as connection:
            items = [dict(row) for row in connection.execute("SELECT * FROM items" + where + " ORDER BY name COLLATE NOCASE", values)]
            categories = [row[0] for row in connection.execute("SELECT DISTINCT category FROM items ORDER BY category COLLATE NOCASE")]
            summary = dict(connection.execute("SELECT count(*) AS item_count, coalesce(sum(CASE WHEN quantity <= reorder_level THEN 1 ELSE 0 END),0) AS low_stock_count, coalesce(sum(CASE WHEN quantity = 0 THEN 1 ELSE 0 END),0) AS out_of_stock_count FROM items").fetchone())
            summary["movement_count"] = connection.execute("SELECT count(*) FROM movements").fetchone()[0]
        return {"items": items, "categories": categories, "summary": summary}

    @app.post("/api/items", status_code=201)
    def create_item(payload: ItemCreate):
        with database() as connection:
            try:
                return add_item(connection, payload.model_dump())
            except sqlite3.IntegrityError:
                raise HTTPException(409, "That SKU already exists. Choose a unique SKU or receive stock into the existing item.")

    @app.get("/api/items/{item_id}")
    def item_detail(item_id: int):
        with database() as connection:
            row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Item not found")
            return dict(row)

    @app.patch("/api/items/{item_id}")
    def edit_item(item_id: int, payload: ItemEdit):
        updates = payload.model_dump(exclude_unset=True)
        version = updates.pop("version")
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Item not found")
            if row["version"] != version:
                raise HTTPException(409, "This item changed in another tab. Close the editor and open it again before saving.")
            changed = {field: value for field, value in updates.items() if row[field] != value}
            if changed:
                connection.execute(f"UPDATE items SET {','.join(field + ' = ?' for field in changed)}, version = version + 1, updated_at = ? WHERE id = ?", [*changed.values(), now(), item_id])
            return dict(connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone())

    @app.get("/api/movements")
    def list_movements(item_id: int | None = None, kind: Literal["receive", "dispatch"] | None = None, limit: int = Query(default=50, ge=1, le=200)):
        clauses, values = [], []
        for field, value in (("m.item_id", item_id), ("m.kind", kind)):
            if value is not None:
                clauses.append(f"{field} = ?")
                values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database() as connection:
            count = connection.execute("SELECT count(*) FROM movements m" + where, values).fetchone()[0]
            rows = connection.execute("SELECT m.*, i.sku, i.name, i.unit FROM movements m JOIN items i ON i.id = m.item_id" + where + " ORDER BY m.id DESC LIMIT ?", [*values, limit])
            return {"items": [dict(row) for row in rows], "total": count, "limit": limit}

    @app.post("/api/movements", status_code=201)
    def move_stock(payload: MovementCreate):
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute("SELECT * FROM movements WHERE request_id = ?", (str(payload.request_id),)).fetchone()
            if previous:
                if any(previous[field] != getattr(payload, field) for field in ("item_id", "kind", "quantity", "reason", "reference")):
                    raise HTTPException(409, "This request ID was already used for a different movement.")
                return dict(previous)
            row = connection.execute("SELECT * FROM items WHERE id = ?", (payload.item_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Item not found")
            delta = payload.quantity if payload.kind == "receive" else -payload.quantity
            balance = row["quantity"] + delta
            if balance < 0:
                raise HTTPException(409, f"Only {row['quantity']} {row['unit']} are available. Reduce the dispatch quantity or receive stock first.")
            if balance > MAX_STOCK:
                raise HTTPException(409, f"Stock cannot exceed {MAX_STOCK:,} per item.")
            stamp = now()
            connection.execute("UPDATE items SET quantity = ?, version = version + 1, updated_at = ? WHERE id = ?", (balance, stamp, payload.item_id))
            cursor = connection.execute("INSERT INTO movements(item_id,kind,quantity,balance_before,balance_after,reason,reference,request_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                        (payload.item_id, payload.kind, payload.quantity, row["quantity"], balance, payload.reason, payload.reference, str(payload.request_id), stamp))
            return dict(connection.execute("SELECT * FROM movements WHERE id = ?", (cursor.lastrowid,)).fetchone())

    @app.post("/api/demo/seed")
    def seed():
        samples = [
            ("CAB-USBC-2M", "USB-C cable · 2 metre", "Accessories", "A-01", "units", 42, 15),
            ("HUB-7PORT", "Seven-port desktop hub", "Accessories", "A-02", "units", 8, 10),
            ("LABEL-THERM", "Thermal shipping labels", "Packing", "B-01", "rolls", 24, 8),
            ("BOX-MED", "Medium shipping boxes", "Packing", "B-03", "packs", 3, 6),
            ("ADAPT-65W", "65W travel adapter", "Power", "C-01", "units", 0, 5),
            ("BATT-AA", "Rechargeable AA batteries", "Power", "C-02", "packs", 18, 6),
        ]
        with database() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM settings WHERE key = 'demo_seeded'").fetchone():
                return {"added": 0, "message": "Sample inventory has already been added."}
            added = 0
            for sku, name, category, location, unit, quantity, reorder_level in samples:
                if connection.execute("SELECT 1 FROM items WHERE sku = ?", (sku,)).fetchone():
                    continue
                add_item(connection, dict(sku=sku, name=name, category=category, location=location, unit=unit, quantity=quantity, reorder_level=reorder_level))
                added += 1
            connection.execute("INSERT INTO settings VALUES('demo_seeded','1')")
            return {"added": added, "message": f"Added {added} sample items. Existing inventory is unchanged."}

    frontend = PROJECT / "frontend"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
