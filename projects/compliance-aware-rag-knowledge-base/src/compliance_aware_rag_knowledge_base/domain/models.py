from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"
    CONTRACTOR = "contractor"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class Identity(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    role: Role
    teams: List[str] = Field(default_factory=list)
    clearance: Sensitivity = Sensitivity.INTERNAL


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1)
    filename: str = "document.txt"
    file_type: str = "text/plain"
    checksum_sha256: str = ""
    parser: str = "plain-text"
    owner: str = "system"
    team: str = "general"
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    source: str = "upload"
    tags: List[str] = Field(default_factory=list)
    retention_days: int = Field(default=365, ge=1, le=3650)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    allowed_roles: List[Role]
    allowed_teams: List[str] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.ACTIVE
    version: int = Field(default=1, ge=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=self.retention_days)


class Chunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    document_title: str = ""
    content: str
    embedding: List[float] = Field(default_factory=list)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    allowed_roles: List[Role]


class Query(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    user_role: Role
    user_teams: List[str] = Field(default_factory=list)
    clearance: Sensitivity = Sensitivity.INTERNAL
    text: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    timestamp: datetime = Field(default_factory=utc_now)


class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    quote: str
    start_char: int
    end_char: int
    lexical_score: float = Field(ge=0, le=1)
    vector_score: float = Field(ge=0, le=1)
    relevance_score: float = Field(ge=0, le=1)


class Answer(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    text: str
    citations: List[Citation]
    confidence_score: float = Field(default=0, ge=0, le=1)
    low_confidence: bool = False
    abstained: bool = False
    prompt_version: str = "grounded-extractive-v1"
    model: str = "deterministic-extractive"
    generated_at: datetime = Field(default_factory=utc_now)


class AuditEventType(str, Enum):
    DOCUMENT_INGESTED = "document_ingested"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_DELETED = "document_deleted"
    DOCUMENT_RESTORED = "document_restored"
    RETENTION_ENFORCED = "retention_enforced"
    QUERY_SUBMITTED = "query_submitted"
    ANSWER_GENERATED = "answer_generated"
    POLICY_DENIED = "policy_denied"
    FEEDBACK_RECORDED = "feedback_recorded"
    REDACTION_CHANGED = "redaction_changed"
    EVALUATION_RUN = "evaluation_run"


class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: AuditEventType
    actor_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    details: Dict[str, Any]


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=240)
    owner: Optional[str] = Field(default=None, min_length=1, max_length=120)
    team: Optional[str] = Field(default=None, min_length=1, max_length=120)
    sensitivity: Optional[Sensitivity] = None
    allowed_roles: Optional[List[Role]] = None
    allowed_teams: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    retention_days: Optional[int] = Field(default=None, ge=1, le=3650)


class RedactionRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    pattern: str = Field(min_length=1, max_length=500)
    replacement: str = "[REDACTED]"
    enabled: bool = True
    apply_to_ingestion: bool = True
    apply_to_audit: bool = True
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)


class Feedback(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    answer_id: UUID
    user_id: str
    rating: int = Field(ge=1, le=5)
    reason: str = Field(default="", max_length=1000)
    created_at: datetime = Field(default_factory=utc_now)


class GoldenQuestion(BaseModel):
    question: str = Field(min_length=2)
    role: Role
    teams: List[str] = Field(default_factory=list)
    clearance: Sensitivity = Sensitivity.INTERNAL
    expected_keywords: List[str] = Field(default_factory=list)
    should_abstain: bool = False


class EvaluationRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utc_now)
    question_count: int
    retrieval_hit_rate: float
    citation_validity_rate: float
    abstention_accuracy: float
    permission_leak_count: int
    average_latency_ms: float
    overall_status: str
    cases: List[Dict[str, Any]] = Field(default_factory=list)

