from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    case_id: str = Field(min_length=1, max_length=200)
    activity: str = Field(min_length=1, max_length=200)
    timestamp: datetime
    resource: Optional[str] = Field(default=None, max_length=200)
    lifecycle: Optional[str] = Field(default=None, max_length=40)
    cost: Optional[float] = None
    event_id: Optional[str] = Field(default=None, max_length=200)

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include an explicit timezone")
        return value.astimezone(timezone.utc)


class AnalysisConfig(BaseModel):
    sla_seconds: float = Field(default=86_400, gt=0)
    bottleneck_seconds: float = Field(default=86_400, ge=0)
    bottleneck_min_frequency: int = Field(default=1, ge=1)


class Transition(BaseModel):
    source: str
    target: str
    frequency: int
    case_coverage: float = 0.0
    avg_duration_seconds: float
    median_duration_seconds: float = 0.0
    p95_duration_seconds: float = 0.0


class Variant(BaseModel):
    id: str
    activities_sequence: List[str]
    frequency: int
    coverage: float = 0.0


class CaseMetric(BaseModel):
    case_id: str
    event_count: int
    start_activity: str
    end_activity: str
    duration_seconds: float
    rework_count: int


class SLABreach(BaseModel):
    case_id: str
    duration_seconds: float
    sla_seconds: float
    exceeded_by_seconds: float


class ResourceMetric(BaseModel):
    resource: str
    event_count: int
    case_count: int
    handoffs_in: int = 0


class Recommendation(BaseModel):
    title: str
    description: str
    expected_impact: str
    evidence: List[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=100)
    validation_step: str = "Measure the same metric before and after a limited pilot."
    rollback_guardrail: str = "Disable the automation if errors or cycle time regress."


class DataQuality(BaseModel):
    accepted_events: int
    rejected_rows: int = 0
    duplicate_events: int = 0
    single_event_cases: int = 0
    issues: List[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    algorithm_version: str = "2026.1"
    total_cases: int
    total_events: int
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)
    data_quality: DataQuality
    variants: List[Variant]
    transitions: List[Transition]
    bottlenecks: List[Transition]
    rework_loops: List[str]
    case_metrics: List[CaseMetric] = Field(default_factory=list)
    sla_breaches: List[SLABreach] = Field(default_factory=list)
    resources: List[ResourceMetric] = Field(default_factory=list)
    ai_summary: str
    recommendations: List[Recommendation]
    created_at: datetime = Field(default_factory=utc_now)


class ImportPayload(BaseModel):
    content: str = Field(min_length=1, max_length=5_000_000)
    mapping: Dict[str, str] = Field(default_factory=dict)
    config: AnalysisConfig = Field(default_factory=AnalysisConfig)
