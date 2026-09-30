from __future__ import annotations

from collections import defaultdict
import json
import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple

from smart_network_capacity_planner.domain.models import TelemetryData, WhatIfScenario


class TelemetryConflictError(ValueError):
    """Raised when the same link/timestamp is submitted with different values."""


class TelemetryRepository:
    """Thread-safe local repository.

    The interface intentionally stays storage-agnostic so a Timescale/PostgreSQL
    adapter can replace this deterministic local store without changing services.
    """

    def __init__(self, state_file: Optional[str] = None) -> None:
        self._data: Dict[str, Dict[str, TelemetryData]] = defaultdict(dict)
        self._scenarios: Dict[str, List[WhatIfScenario]] = defaultdict(list)
        self._lock = RLock()
        configured_path = state_file if state_file is not None else os.getenv("CAPACITY_STATE_FILE", "")
        self._state_file = Path(configured_path) if configured_path else None
        self._load()

    def _load(self) -> None:
        if self._state_file is None or not self._state_file.exists():
            return
        payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        for link_id, samples in payload.get("telemetry", {}).items():
            for raw_sample in samples:
                sample = TelemetryData.model_validate(raw_sample)
                self._data[link_id][self._key(sample)] = sample
        for link_id, scenarios in payload.get("scenarios", {}).items():
            self._scenarios[link_id] = [WhatIfScenario.model_validate(item) for item in scenarios]

    def _persist(self) -> None:
        if self._state_file is None:
            return
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "telemetry": {
                link_id: [sample.model_dump(mode="json") for sample in sorted(samples.values(), key=lambda item: item.timestamp)]
                for link_id, samples in self._data.items()
            },
            "scenarios": {
                link_id: [scenario.model_dump(mode="json") for scenario in scenarios]
                for link_id, scenarios in self._scenarios.items()
            },
        }
        temporary = self._state_file.with_suffix(self._state_file.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._state_file)

    @staticmethod
    def _key(sample: TelemetryData) -> str:
        return sample.timestamp.isoformat()

    def save_batch(self, batch: List[TelemetryData]) -> Tuple[int, int]:
        accepted = 0
        duplicates = 0
        with self._lock:
            pending: Dict[Tuple[str, str], TelemetryData] = {}
            for sample in batch:
                key = self._key(sample)
                identity = (sample.link_id, key)
                existing = pending.get(identity, self._data.get(sample.link_id, {}).get(key))
                if existing is not None:
                    if existing == sample:
                        duplicates += 1
                        continue
                    raise TelemetryConflictError(
                        f"conflicting sample already exists for {sample.link_id} at {key}"
                    )
                pending[identity] = sample
                accepted += 1
            # Commit only after the complete batch passes conflict checks.
            # Rejected uploads must leave the live and persisted views identical.
            for (link_id, key), sample in pending.items():
                self._data[link_id][key] = sample
            if accepted:
                self._persist()
        return accepted, duplicates

    def get_by_link(self, link_id: str) -> List[TelemetryData]:
        with self._lock:
            return sorted(self._data.get(link_id, {}).values(), key=lambda item: item.timestamp)

    def list_link_ids(self) -> List[str]:
        with self._lock:
            return sorted(link_id for link_id, samples in self._data.items() if samples)

    def sample_count(self) -> int:
        with self._lock:
            return sum(len(samples) for samples in self._data.values())

    def save_scenario(self, link_id: str, scenario: WhatIfScenario) -> WhatIfScenario:
        with self._lock:
            self._scenarios[link_id].append(scenario)
            self._persist()
        return scenario

    def list_scenarios(self, link_id: str) -> List[WhatIfScenario]:
        with self._lock:
            return list(self._scenarios.get(link_id, []))

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._scenarios.clear()
            self._persist()
