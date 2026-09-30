from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    INLINE = "inline"
    CSV = "csv"
    JSON = "json"
    POSTGRES = "postgres"
    API = "api"
    S3 = "s3"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class DataSource(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(default="Dataset", min_length=1, max_length=160)
    type: SourceType
    config: Dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="data-platform", min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def safe_view(self) -> "DataSource":
        hidden = {"password", "token", "secret", "api_key", "dsn", "connection_string"}
        safe_config = {
            key: ("***" if key.lower() in hidden or key.lower().endswith("_secret") else value)
            for key, value in self.config.items()
        }
        return self.model_copy(update={"config": safe_config})


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    null_ratio: float = Field(ge=0, le=1)
    unique_count: int = Field(ge=0)
    uniqueness_ratio: float = Field(ge=0, le=1)
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    mean: Optional[float] = None
    standard_deviation: Optional[float] = None
    top_values: Dict[str, int] = Field(default_factory=dict)


class DatasetProfile(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    row_count: int = Field(ge=0)
    sampled: bool = False
    sample_size: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    columns: List[ColumnProfile] = Field(default_factory=list)
    data_hash: str
    source_freshness_at: Optional[datetime] = None
    is_baseline: bool = False


class Rule(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    source_id: str
    rule_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.HIGH
    enabled: bool = True
    description: str = ""
    version: int = Field(default=1, ge=1)


class RuleResult(BaseModel):
    rule_id: str
    passed: bool
    severity: Severity
    details: str
    observed: Any = None
    expected: Any = None


class DriftSignal(BaseModel):
    drift_type: str
    column: Optional[str] = None
    score: float = Field(ge=0)
    threshold: float = Field(ge=0)
    details: str


class DriftResult(BaseModel):
    has_drift: bool
    details: str
    signals: List[DriftSignal] = Field(default_factory=list)
    baseline_profile_id: Optional[UUID] = None


class IssueEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    actor: str = "system"
    action: str
    note: str = ""


class Issue(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    fingerprint: str
    source_id: str
    title: str
    description: str
    status: IssueStatus = IssueStatus.OPEN
    severity: Severity
    owner: Optional[str] = None
    suggested_remediation: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    occurrence_count: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    timeline: List[IssueEvent] = Field(default_factory=list)


class IssueUpdate(BaseModel):
    status: Optional[IssueStatus] = None
    owner: Optional[str] = Field(default=None, max_length=120)
    comment: Optional[str] = Field(default=None, max_length=1000)
    actor: str = Field(default="operator", min_length=1, max_length=120)


class ObservationReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=utc_now)
    profile: DatasetProfile
    rule_results: List[RuleResult]
    drift_result: DriftResult
    health_score: float = Field(ge=0, le=100)
    health_status: str
    issues_created: List[Issue] = Field(default_factory=list)
    issues_updated: List[Issue] = Field(default_factory=list)


class DatasetOverview(BaseModel):
    source: DataSource
    latest_profile: Optional[DatasetProfile]
    health_score: Optional[float]
    health_status: str
    active_issue_count: int
    rule_count: int


class ConnectorPreview(BaseModel):
    source_id: str
    row_count: int
    columns: List[str]
    rows: List[Dict[str, Any]]
    truncated: bool


class DeliveryResult(BaseModel):
    issue_id: UUID
    destination: str
    delivered: bool
    payload: Dict[str, Any]
    message: str

