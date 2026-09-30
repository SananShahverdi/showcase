from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Dict, Optional, Literal
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

class EventType(str, Enum):
    TRANSACTION = "transaction"
    LOGIN = "login"
    DEVICE_CHANGE = "device_change"
    PAYMENT = "payment"

class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    type: EventType
    amount: float = Field(default=0.0, ge=0.0, le=10_000_000.0)
    location: str = "US"
    device_id: str = "device_1"
    outcome: Literal["success", "failed"] = "success"
    schema_version: str = "1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        # Legacy local events omit an offset; interpret them as UTC just like
        # the seeded data, then compare every event on the same timeline.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

class RiskFeatures(BaseModel):
    velocity_1h: int = 0
    amount_sum_24h: float = 0.0
    distinct_locations_24h: int = 1
    distinct_devices_24h: int = 1
    failed_attempts_1h: int = 0
    amount_spike_ratio: float = 1.0
    geo_anomaly: bool = False
    device_changed: bool = False
    history_events: int = 0
    is_late: bool = False

class Score(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    event_id: UUID
    anomaly_score: float
    rule_score: float
    total_risk_score: float
    reason_codes: List[str]
    contributions: Dict[str, float] = Field(default_factory=dict)
    model_version: str = "statistical-v1"
    policy_version: str = "rules-v1"

class AnalystFeedback(str, Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    PENDING = "pending"

class Alert(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event: Event
    features: RiskFeatures
    score: Score
    status: AnalystFeedback = AnalystFeedback.PENDING
    assigned_to: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProcessingStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    LATE = "late"

class ProcessingResult(BaseModel):
    event_id: UUID
    status: ProcessingStatus
    features: Optional[RiskFeatures] = None
    score: Optional[Score] = None
    alert: Optional[Alert] = None
    message: str

class FeedbackRequest(BaseModel):
    feedback: AnalystFeedback
    actor: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=3, max_length=500)
    expected_version: int = Field(default=1, ge=1)

    @field_validator("feedback")
    @classmethod
    def must_be_decision(cls, value: "AnalystFeedback") -> "AnalystFeedback":
        # "pending" is the initial state, not something an analyst can record.
        if value == AnalystFeedback.PENDING:
            raise ValueError("feedback must be a review decision, not pending")
        return value

class MetricsDashboard(BaseModel):
    total_events: int
    total_alerts: int
    pending_alerts: int
    reviewed_alerts: int
    true_positives: int
    false_positives: int
    false_positive_rate: float
    precision: float
    average_risk_score: float
    drift_index: Optional[float] = None
    reason_code_counts: Dict[str, int] = Field(default_factory=dict)
