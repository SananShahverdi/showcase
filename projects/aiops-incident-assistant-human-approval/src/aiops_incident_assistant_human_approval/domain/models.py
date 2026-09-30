from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class IncidentType(str, Enum):
    LATENCY_SPIKE = "latency_spike"
    DEPENDENCY_FAILURE = "dependency_failure"
    HIGH_ERROR_RATE = "high_error_rate"
    QUEUE_BACKLOG = "queue_backlog"

class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"

class IncidentSeverity(str, Enum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"

class TelemetryData(BaseModel):
    logs: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    traces: List[Dict[str, Any]] = Field(default_factory=list)

class EvidenceReference(BaseModel):
    kind: Literal["log", "metric", "trace", "runbook"]
    source: str
    observation: str

class Incident(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: IncidentType
    service_name: str
    severity: IncidentSeverity = IncidentSeverity.SEV2
    status: IncidentStatus = IncidentStatus.OPEN
    telemetry: TelemetryData = Field(default_factory=TelemetryData)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

class RemediationAction(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    description: str
    command: str
    risk_level: Literal["low", "medium", "high"]
    rollback_command: str
    status: ActionStatus = ActionStatus.PENDING
    policy_reason: str = "Allowed by local command policy"
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None
    decided_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_output: Optional[str] = None

class RemediationPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    incident_id: UUID
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    runbook: str
    evidence: List[EvidenceReference] = Field(default_factory=list)
    actions: List[RemediationAction]
    revision: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PostIncidentReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    incident_id: UUID
    summary: str
    root_cause: str
    actions_taken: List[str]
    time_to_resolution_minutes: float
    evidence: List[EvidenceReference] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    incident_id: UUID
    plan_id: Optional[UUID] = None
    action_id: Optional[UUID] = None
    event_type: str
    actor: str
    detail: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
