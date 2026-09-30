from typing import Dict, List
from uuid import UUID, uuid4

from pydantic import BaseModel

from agentic_ba_automation_platform.adapters.database import Binding, StatePersistence, redacted


class Item(BaseModel):
    name: str
    count: int = 0


class Counter(BaseModel):
    total: int = 0


class Owner:
    def __init__(self):
        self.items: Dict[UUID, Item] = {}
        self.history: List[Item] = []
        self.blobs: Dict[str, bytes] = {}
        self.counter = Counter()


def bindings(owner):
    return [
        Binding("items", lambda: owner.items, Item, UUID),
        Binding("history", lambda: owner.history, Item),
        Binding("blobs", lambda: owner.blobs, bytes),
        Binding("counter", lambda: owner.counter, Counter, setter=lambda value: setattr(owner, "counter", value)),
    ]


def test_state_round_trips_including_in_place_edits_and_deletes(tmp_path):
    url = f"sqlite:///{tmp_path / 'state.sqlite3'}"
    first = Owner()
    store = StatePersistence(url, "test", bindings(first))
    store.restore()
    keep, drop = uuid4(), uuid4()
    first.items[keep] = Item(name="keep")
    first.items[drop] = Item(name="drop")
    first.history.append(Item(name="event"))
    first.blobs["archive"] = b"\x00\xffzip"
    first.counter.total = 3
    assert store.save() == 5
    first.items[keep].count = 7          # in-place edit, no re-assignment
    del first.items[drop]
    assert store.save() == 2             # one changed row, one deleted row
    assert store.save() == 0             # nothing changed

    second = Owner()
    StatePersistence(url, "test", bindings(second)).restore()
    assert list(second.items) == [keep] and second.items[keep].count == 7
    assert [item.name for item in second.history] == ["event"]
    assert second.blobs["archive"] == b"\x00\xffzip"
    assert second.counter.total == 3


def test_namespaces_do_not_collide(tmp_path):
    url = f"sqlite:///{tmp_path / 'shared.sqlite3'}"
    a, b = Owner(), Owner()
    StatePersistence(url, "a", bindings(a)).restore()
    a.items[uuid4()] = Item(name="only in a")
    StatePersistence(url, "a", bindings(a)).save()
    StatePersistence(url, "b", bindings(b)).restore()
    assert b.items == {}


def test_urls_are_redacted():
    assert "secret" not in redacted("postgresql+psycopg2://app:secret@db:5432/state")
