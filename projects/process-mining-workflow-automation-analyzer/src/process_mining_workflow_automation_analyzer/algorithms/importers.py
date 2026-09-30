import csv
import io
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

from pydantic import ValidationError

from process_mining_workflow_automation_analyzer.domain.models import Event


DEFAULT_MAPPING = {
    "case_id": "case_id",
    "activity": "activity",
    "timestamp": "timestamp",
    "resource": "resource",
    "lifecycle": "lifecycle",
    "cost": "cost",
    "event_id": "event_id",
}


def _event_from_row(row: Dict[str, str], mapping: Dict[str, str]) -> Event:
    def read(name: str):
        source = mapping.get(name, DEFAULT_MAPPING[name])
        value = row.get(source)
        return value.strip() if isinstance(value, str) else value

    payload = {"case_id": read("case_id"), "activity": read("activity"), "timestamp": read("timestamp")}
    for optional in ("resource", "lifecycle", "event_id"):
        value = read(optional)
        if value:
            payload[optional] = value
    cost = read("cost")
    if cost not in (None, ""):
        payload["cost"] = cost
    return Event.model_validate(payload)


def parse_csv_events(content: str, mapping: Dict[str, str] | None = None) -> Tuple[List[Event], List[str]]:
    if len(content.encode("utf-8")) > 5_000_000:
        raise ValueError("CSV exceeds the 5 MB import limit")
    mapping = {**DEFAULT_MAPPING, **(mapping or {})}
    reader = csv.DictReader(io.StringIO(content.removeprefix("\ufeff"), newline=""))
    required_columns = {mapping["case_id"], mapping["activity"], mapping["timestamp"]}
    if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
        missing = sorted(required_columns - set(reader.fieldnames or []))
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    events, issues = [], []
    try:
        for row_number, row in enumerate(reader, 2):
            if row_number > 100_001:
                raise ValueError("CSV exceeds the 100,000-row analysis limit")
            try:
                events.append(_event_from_row(row, mapping))
            except (ValidationError, ValueError) as exc:
                issues.append(f"row {row_number}: {exc}")
    except csv.Error as exc:
        raise ValueError(f"Cannot parse CSV: {exc}") from exc
    return events, issues


def _attributes(element: ET.Element) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for child in element:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in {"string", "date", "float", "int"} and child.get("key"):
            values[child.get("key")] = child.get("value", "")
    return values


def parse_xes_events(content: str) -> Tuple[List[Event], List[str]]:
    if len(content.encode("utf-8")) > 5_000_000:
        raise ValueError("XES-like document exceeds the 5 MB import limit")
    upper = content.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise ValueError("DTD and entity declarations are not allowed")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed XES-like XML: {exc}") from exc
    events, issues = [], []
    trace_count = 0
    for trace in root.iter():
        if trace.tag.rsplit("}", 1)[-1] != "trace":
            continue
        trace_count += 1
        trace_values = _attributes(trace)
        case_id = trace.get("case_id") or trace_values.get("concept:name")
        for index, node in enumerate(trace, 1):
            if node.tag.rsplit("}", 1)[-1] != "event":
                continue
            values = _attributes(node)
            payload = {
                "case_id": node.get("case_id") or case_id,
                "activity": node.get("activity") or values.get("concept:name"),
                "timestamp": node.get("timestamp") or values.get("time:timestamp"),
                "resource": node.get("resource") or values.get("org:resource"),
                "event_id": node.get("event_id") or values.get("identity:id"),
                "lifecycle": node.get("lifecycle") or values.get("lifecycle:transition"),
                "cost": node.get("cost") or values.get("cost:total"),
            }
            try:
                events.append(Event.model_validate({key: value for key, value in payload.items() if value not in (None, "")}))
            except (ValidationError, ValueError) as exc:
                issues.append(f"trace {trace_count}, event {index}: {exc}")
            if len(events) + len(issues) > 100_000:
                raise ValueError("XES-like document exceeds the 100,000-event limit")
    if trace_count == 0:
        for index, node in enumerate(root, 1):
            if node.tag.rsplit("}", 1)[-1] != "event":
                continue
            try:
                events.append(Event.model_validate(dict(node.attrib)))
            except (ValidationError, ValueError) as exc:
                issues.append(f"event {index}: {exc}")
    return events, issues
