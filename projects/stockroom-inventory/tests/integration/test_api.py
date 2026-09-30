from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from stockroom_inventory.api.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "inventory.sqlite3")) as client:
        yield client


def add_item(client, **values):
    return client.post("/api/items", json={"sku": "TEST-01", "name": "Test item", "quantity": 10, **values}).json()


def test_receive_dispatch_and_ledger_are_consistent(client):
    item = add_item(client)
    received = client.post("/api/movements", json={"item_id": item["id"], "kind": "receive", "quantity": 4, "reason": "Supplier delivery"})
    assert received.status_code == 201
    assert received.json()["balance_after"] == 14
    dispatched = client.post("/api/movements", json={"item_id": item["id"], "kind": "dispatch", "quantity": 6, "reason": "Order packed"})
    assert dispatched.json()["balance_before"] == 14
    assert dispatched.json()["balance_after"] == 8
    assert client.get(f"/api/items/{item['id']}").json()["quantity"] == 8
    ledger = client.get(f"/api/movements?item_id={item['id']}").json()
    assert len(ledger["items"]) == 3
    assert ledger["items"][-1]["reason"] == "Opening stock"


def test_overdraft_rolls_back_balance_and_ledger(client):
    item = add_item(client, quantity=2)
    response = client.post("/api/movements", json={"item_id": item["id"], "kind": "dispatch", "quantity": 3, "reason": "Order packed"})
    assert response.status_code == 409
    assert client.get(f"/api/items/{item['id']}").json()["quantity"] == 2
    assert client.get("/api/movements").json()["total"] == 1


def test_concurrent_dispatch_cannot_oversell(client):
    item = add_item(client, quantity=5)
    def dispatch(_):
        return client.post("/api/movements", json={"item_id": item["id"], "kind": "dispatch", "quantity": 4, "reason": "Order packed"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(dispatch, range(2))) == [201, 409]
    assert client.get(f"/api/items/{item['id']}").json()["quantity"] == 1
    assert client.get("/api/movements").json()["total"] == 2


def test_movement_request_id_prevents_duplicate_effects(client):
    item = add_item(client)
    payload = {"item_id": item["id"], "kind": "receive", "quantity": 2, "reason": "Delivery", "request_id": str(uuid4())}
    first = client.post("/api/movements", json=payload).json()
    assert client.post("/api/movements", json=payload).json()["id"] == first["id"]
    assert client.get(f"/api/items/{item['id']}").json()["quantity"] == 12
    assert client.post("/api/movements", json={**payload, "quantity": 3}).status_code == 409


def test_validation_filters_and_edit_conflicts(client):
    item = add_item(client, quantity=2, reorder_level=3)
    assert client.post("/api/items", json={"sku": "test-01", "name": "Duplicate"}).status_code == 409
    assert client.post("/api/items", json={"sku": "EMPTY", "name": "   "}).status_code == 422
    assert client.post("/api/movements", json={"item_id": item["id"], "kind": "receive", "quantity": -1, "reason": "Invalid"}).status_code == 422
    assert client.post("/api/movements", json={"item_id": item["id"], "kind": "receive", "quantity": 1.5, "reason": "Invalid"}).status_code == 422
    assert len(client.get("/api/items?low_stock=true&q=test").json()["items"]) == 1
    assert client.get("/api/items?q=%").json()["items"] == []
    assert client.patch(f"/api/items/{item['id']}", json={"version": 1, "location": "Shelf B"}).status_code == 200
    assert client.patch(f"/api/items/{item['id']}", json={"version": 1, "location": "Shelf C"}).status_code == 409
    assert client.patch(f"/api/items/{item['id']}", json={"version": 2, "quantity": 99}).status_code == 422


def test_seed_is_idempotent_preserves_existing_sku_and_storage(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(path)) as client:
        add_item(client, sku="CAB-USBC-2M", quantity=99)
        assert client.post("/api/demo/seed").json()["added"] == 5
        assert client.post("/api/demo/seed").json()["added"] == 0
        assert client.get("/api/items?q=CAB-USBC").json()["items"][0]["quantity"] == 99
    with TestClient(create_app(path)) as client:
        assert client.get("/api/items").json()["summary"]["item_count"] == 6
