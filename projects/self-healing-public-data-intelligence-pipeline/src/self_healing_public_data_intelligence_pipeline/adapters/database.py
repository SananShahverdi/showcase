"""Optional SQL persistence for the in-process repositories.

With no database URL configured the application keeps its documented
in-memory behavior. With a URL (SQLite or PostgreSQL), registered state
collections are restored at startup and synchronized after every successful
write request: one transaction per request, writing only changed documents
and deleting removed ones. Because synchronization happens at the request
boundary, in-place edits to repository objects are captured as well.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional

from pydantic import TypeAdapter
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from .orm import Base, DocumentRecord

logger = logging.getLogger(__name__)
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_database_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
    else:
        engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


def redacted(url: str) -> str:
    """The URL with any password hidden, safe for logs and health output."""
    return make_url(url).render_as_string(hide_password=True)


@dataclass
class Binding:
    """One persisted collection owned by a repository or service.

    ``target`` returns the live container. A dict is stored one document per
    key; a list is stored as one document and restored in place. For any other
    object (for example a metrics model) pass ``setter`` to restore it.
    """

    name: str
    target: Callable[[], Any]
    value_type: Any
    key_type: Any = str
    setter: Optional[Callable[[Any], None]] = None

    def __post_init__(self) -> None:
        self._binary = self.value_type is bytes
        self._keys = TypeAdapter(self.key_type)
        container = self.target()
        if isinstance(container, list):
            self.kind = "list"
            self._values = TypeAdapter(List[self.value_type])
        elif isinstance(container, dict):
            self.kind = "dict"
            self._values = TypeAdapter(self.value_type)
        else:
            if self.setter is None:
                raise ValueError(f"Binding '{self.name}' holds a single object and needs a setter")
            self.kind = "value"
            self._values = TypeAdapter(self.value_type)

    def documents(self) -> Dict[str, Any]:
        container = self.target()
        if self.kind == "dict":
            return {key if isinstance(key, str) else str(key): value for key, value in list(container.items())}
        return {"__all__": list(container) if self.kind == "list" else container}

    def load(self, documents: Dict[str, Any]) -> None:
        container = self.target()
        if self.kind == "dict":
            container.clear()
            container.update({key if self.key_type is str else self._keys.validate_python(key): value for key, value in documents.items()})
        elif "__all__" in documents:
            if self.kind == "list":
                container[:] = documents["__all__"]
            else:
                self.setter(documents["__all__"])

    def encode(self, value: Any) -> str:
        if self._binary:
            return json.dumps(base64.b64encode(value).decode("ascii"))
        return self._values.dump_json(value).decode("utf-8")

    def decode(self, payload: str) -> Any:
        if self._binary:
            return base64.b64decode(json.loads(payload))
        return self._values.validate_json(payload)


class StatePersistence:
    def __init__(self, url: str, namespace: str, bindings: Iterable[Binding]) -> None:
        self.url = url
        self.namespace = namespace
        self.bindings = list(bindings)
        self.engine = create_database_engine(url)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)
        self._lock = threading.Lock()
        self._digests: Dict[str, Dict[str, str]] = {}

    def _collection(self, binding: Binding) -> str:
        return f"{self.namespace}.{binding.name}"

    def restore(self) -> int:
        """Load stored documents into the live dicts, replacing their contents."""
        loaded = 0
        with self._lock, Session(self.engine) as session:
            for binding in self.bindings:
                rows = session.scalars(select(DocumentRecord).where(DocumentRecord.collection == self._collection(binding))).all()
                if rows:
                    binding.load({row.key: binding.decode(row.payload) for row in rows})
                self._digests[binding.name] = {row.key: row.digest for row in rows}
                loaded += len(rows)
        logger.info("Restored %d documents for %s from %s", loaded, self.namespace, redacted(self.url))
        return loaded

    def save(self) -> int:
        """Write changed documents and delete removed ones in a single transaction."""
        with self._lock:
            snapshot = []
            for binding in self.bindings:
                documents = {}
                for key, value in binding.documents().items():
                    payload = binding.encode(value)
                    documents[key] = (payload, hashlib.sha256(payload.encode("utf-8")).hexdigest())
                snapshot.append((binding, documents))
            changes = 0
            now = datetime.now(timezone.utc)
            with self._sessions.begin() as session:
                for binding, documents in snapshot:
                    previous = self._digests.get(binding.name, {})
                    collection = self._collection(binding)
                    removed = [key for key in previous if key not in documents]
                    if removed:
                        session.execute(delete(DocumentRecord).where(DocumentRecord.collection == collection, DocumentRecord.key.in_(removed)))
                    for key, (payload, digest) in documents.items():
                        if previous.get(key) != digest:
                            session.merge(DocumentRecord(collection=collection, key=key, payload=payload, digest=digest, updated_at=now))
                    changes += len(removed) + sum(previous.get(key) != digest for key, (_, digest) in documents.items())
            for binding, documents in snapshot:
                self._digests[binding.name] = {key: digest for key, (_, digest) in documents.items()}
            return changes

    def describe(self) -> dict:
        return {"backend": make_url(self.url).get_backend_name(), "url": redacted(self.url),
                "collections": [binding.name for binding in self.bindings]}


def install(app, persistence: Optional[StatePersistence]) -> None:
    """Restore state now and synchronize it after each successful write request."""
    app.state.persistence = persistence
    if persistence is None:
        return
    persistence.restore()

    @app.middleware("http")
    async def _unit_of_work(request, call_next):
        response = await call_next(request)
        if request.method in WRITE_METHODS and response.status_code < 400:
            try:
                await run_in_threadpool(persistence.save)
            except SQLAlchemyError:
                logger.exception("Could not persist state to %s", redacted(persistence.url))
                return JSONResponse({"detail": "The change was applied but could not be saved to the database. Check the database connection and retry."}, status_code=503)
        return response
