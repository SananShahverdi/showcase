from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

class ArtifactType(str, Enum):
    USER_STORY = "user_story"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    RISK = "risk"
    ASSUMPTION = "assumption"
    PROCESS_SUMMARY = "process_summary"
    IMPLEMENTATION_TICKET = "implementation_ticket"

class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"

class Document(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str
    file_type: str
    content: str
    content_hash: str = ""
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Chunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: str
    start_index: int
    end_index: int

class Citation(BaseModel):
    chunk_id: UUID
    quote: str
    start_index: int = 0
    end_index: int = 0

class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: ArtifactType
    content: str
    citations: List[Citation] = Field(default_factory=list)
    status: ArtifactStatus = ArtifactStatus.DRAFT
    query: str = ""
    generator: str = "local-grounded-v1"
    prompt_version: str = "2026-07-11"
    revision: int = 1
    reviewer_id: Optional[str] = None
    review_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    action: str
    user_id: str
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExportResult(BaseModel):
    target: str
    mode: str
    payload: Dict[str, Any]
    remote_url: Optional[str] = None
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
