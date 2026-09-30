from uuid import UUID

import pytest
from pydantic import ValidationError

from stockroom_inventory.api.app import MAX_STOCK, ItemCreate, ItemEdit, MovementCreate


def test_item_defaults_and_whole_unit_quantities():
    item = ItemCreate(sku="CAB-01", name=" Cable ")
    assert (item.name, item.category, item.location, item.unit, item.quantity, item.reorder_level) == ("Cable", "General", "Unassigned", "units", 0, 5)
    with pytest.raises(ValidationError):
        ItemCreate(sku="CAB-01", name="Cable", quantity=1.5)
    with pytest.raises(ValidationError):
        ItemCreate(sku="CAB-01", name="Cable", quantity="3")


@pytest.mark.parametrize("sku", ["", "-LEADING-DASH", "HAS SPACE", "SEMI;COLON", "X" * 41])
def test_item_rejects_unsafe_skus(sku):
    with pytest.raises(ValidationError):
        ItemCreate(sku=sku, name="Item")


def test_item_stock_is_bounded():
    assert ItemCreate(sku="MAX", name="Max", quantity=MAX_STOCK).quantity == MAX_STOCK
    for quantity in (-1, MAX_STOCK + 1):
        with pytest.raises(ValidationError):
            ItemCreate(sku="BAD", name="Bad", quantity=quantity)


def test_edit_cannot_change_immutable_fields_or_null_values():
    for field, value in (("sku", "NEW"), ("unit", "packs"), ("quantity", 3)):
        with pytest.raises(ValidationError):
            ItemEdit(version=1, **{field: value})
    with pytest.raises(ValidationError):
        ItemEdit(version=1, name=None)


def test_movement_requires_positive_quantity_and_reason_and_generates_request_ids():
    first = MovementCreate(item_id=1, kind="receive", quantity=2, reason="Supplier delivery")
    second = MovementCreate(item_id=1, kind="receive", quantity=2, reason="Supplier delivery")
    assert isinstance(first.request_id, UUID) and first.request_id != second.request_id
    for payload in ({"quantity": 0}, {"reason": "ok"}, {"kind": "adjust"}, {"request_id": "not-a-uuid"}):
        with pytest.raises(ValidationError):
            MovementCreate(**{"item_id": 1, "kind": "dispatch", "quantity": 1, "reason": "Order packed", **payload})
