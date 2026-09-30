from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from autonomous_data_quality_observatory.domain.models import (
    DataSource,
    DatasetProfile,
    Issue,
    IssueEvent,
    IssueStatus,
    ObservationReport,
    Rule,
    utc_now,
)


class MetadataRepository:
    def __init__(self, state_file: Optional[str] = None) -> None:
        self.sources: Dict[str, DataSource] = {}
        self.profiles: Dict[str, List[DatasetProfile]] = {}
        self.rules: Dict[str, Dict[str, Rule]] = {}
        self.issues: Dict[UUID, Issue] = {}
        self.reports: Dict[str, List[ObservationReport]] = {}
        self._lock = RLock()
        configured = state_file if state_file is not None else os.getenv("DATA_QUALITY_STATE_FILE", "")
        self._state_file = Path(configured) if configured else None
        self._load()

    def _load(self) -> None:
        if self._state_file is None or not self._state_file.exists():
            return
        payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        self.sources = {item["id"]: DataSource.model_validate(item) for item in payload.get("sources", [])}
        self.profiles = {
            source_id: [DatasetProfile.model_validate(item) for item in profiles]
            for source_id, profiles in payload.get("profiles", {}).items()
        }
        self.rules = {
            source_id: {item["id"]: Rule.model_validate(item) for item in rules}
            for source_id, rules in payload.get("rules", {}).items()
        }
        self.issues = {
            UUID(item["id"]): Issue.model_validate(item) for item in payload.get("issues", [])
        }
        self.reports = {
            source_id: [ObservationReport.model_validate(item) for item in reports]
            for source_id, reports in payload.get("reports", {}).items()
        }

    def _persist(self) -> None:
        if self._state_file is None:
            return
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sources": [item.model_dump(mode="json") for item in self.sources.values()],
            "profiles": {key: [item.model_dump(mode="json") for item in values] for key, values in self.profiles.items()},
            "rules": {key: [item.model_dump(mode="json") for item in values.values()] for key, values in self.rules.items()},
            "issues": [item.model_dump(mode="json") for item in self.issues.values()],
            "reports": {key: [item.model_dump(mode="json") for item in values] for key, values in self.reports.items()},
        }
        temporary = self._state_file.with_suffix(self._state_file.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._state_file)

    def save_source(self, source: DataSource) -> DataSource:
        with self._lock:
            existing = self.sources.get(source.id)
            if existing:
                source.created_at = existing.created_at
                source.updated_at = utc_now()
            self.sources[source.id] = source
            self.profiles.setdefault(source.id, [])
            self.rules.setdefault(source.id, {})
            self.reports.setdefault(source.id, [])
            self._persist()
        return source

    def get_source(self, source_id: str) -> Optional[DataSource]:
        return self.sources.get(source_id)

    def list_sources(self) -> List[DataSource]:
        return sorted(self.sources.values(), key=lambda item: item.id)

    def save_profile(self, profile: DatasetProfile) -> DatasetProfile:
        with self._lock:
            self.profiles.setdefault(profile.source_id, []).append(profile)
            self._persist()
        return profile

    def list_profiles(self, source_id: str) -> List[DatasetProfile]:
        return sorted(self.profiles.get(source_id, []), key=lambda item: item.timestamp, reverse=True)

    def get_latest_profile(self, source_id: str) -> Optional[DatasetProfile]:
        profiles = self.list_profiles(source_id)
        return profiles[0] if profiles else None

    def get_baseline_profile(self, source_id: str) -> Optional[DatasetProfile]:
        profiles = self.profiles.get(source_id, [])
        return next((profile for profile in profiles if profile.is_baseline), profiles[0] if profiles else None)

    def set_baseline(self, source_id: str, profile_id: UUID) -> DatasetProfile:
        with self._lock:
            selected: Optional[DatasetProfile] = None
            for profile in self.profiles.get(source_id, []):
                profile.is_baseline = profile.id == profile_id
                if profile.is_baseline:
                    selected = profile
            if selected is None:
                raise ValueError("Profile not found")
            self._persist()
            return selected

    def save_rule(self, rule: Rule) -> Rule:
        with self._lock:
            existing = self.rules.setdefault(rule.source_id, {}).get(rule.id)
            if existing:
                rule.version = existing.version + 1
            self.rules[rule.source_id][rule.id] = rule
            self._persist()
        return rule

    def get_rules(self, source_id: str) -> List[Rule]:
        return sorted(self.rules.get(source_id, {}).values(), key=lambda item: item.id)

    def upsert_issue(self, issue: Issue) -> Tuple[Issue, bool]:
        with self._lock:
            existing = next(
                (
                    current for current in self.issues.values()
                    if current.fingerprint == issue.fingerprint and current.status != IssueStatus.RESOLVED
                ),
                None,
            )
            if existing:
                existing.occurrence_count += 1
                existing.updated_at = utc_now()
                existing.description = issue.description
                existing.evidence = issue.evidence
                existing.timeline.append(IssueEvent(action="reobserved", note=issue.description))
                self._persist()
                return existing, False
            issue.timeline.append(IssueEvent(action="opened", note=issue.description))
            self.issues[issue.id] = issue
            self._persist()
            return issue, True

    def get_issue(self, issue_id: UUID) -> Optional[Issue]:
        return self.issues.get(issue_id)

    def list_issues(self, source_id: Optional[str] = None, active_only: bool = False) -> List[Issue]:
        values = list(self.issues.values())
        if source_id:
            values = [item for item in values if item.source_id == source_id]
        if active_only:
            values = [item for item in values if item.status != IssueStatus.RESOLVED]
        return sorted(values, key=lambda item: item.updated_at, reverse=True)

    def save_issue(self, issue: Issue) -> Issue:
        with self._lock:
            self.issues[issue.id] = issue
            self._persist()
        return issue

    def save_report(self, report: ObservationReport) -> ObservationReport:
        with self._lock:
            self.reports.setdefault(report.profile.source_id, []).append(report)
            self._persist()
        return report

    def list_reports(self, source_id: str) -> List[ObservationReport]:
        return sorted(self.reports.get(source_id, []), key=lambda item: item.generated_at, reverse=True)

    def clear(self) -> None:
        with self._lock:
            self.sources.clear()
            self.profiles.clear()
            self.rules.clear()
            self.issues.clear()
            self.reports.clear()
            self._persist()
