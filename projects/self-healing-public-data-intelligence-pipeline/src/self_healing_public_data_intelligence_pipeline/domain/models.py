from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

class SourceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    BROKEN = "broken"

class Source(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    url: str
    name: str
    status: SourceStatus = SourceStatus.ACTIVE
    rate_limit_ms: int = 1000
    expected_schema: Dict[str, str] = Field(default_factory=lambda: {"title": "str", "price": "float"})

class ExtractionRecipe(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    version: int = 1
    selectors: Dict[str, str] # e.g. {"title": "h1.main-title", "price": ".price-tag"}
    is_active: bool = True
    success_rate: float = 1.0

class CrawlRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    recipe_id: UUID
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    html_snapshot_path: Optional[str] = None
    html_snapshot: str = ""
    dom_fingerprint: str = ""
    schema_drift: bool = False
    extracted_count: int = 0
    valid_count: int = 0
    quarantined_count: int = 0
    success: bool = True

class Record(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    crawl_run_id: UUID
    extracted_data: Dict[str, Any]
    is_valid: bool = True
    quarantined: bool = False

class ValidationFailure(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    record_id: UUID
    crawl_run_id: UUID
    error_message: str
    field: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RepairProposal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    original_recipe_id: UUID
    proposed_selectors: Dict[str, str]
    target_field: str
    rationale: str
    approved: bool = False
    replay_passed: bool = False
    replay_matches: Dict[str, int] = Field(default_factory=dict)
    confidence_score: float = 0.0
