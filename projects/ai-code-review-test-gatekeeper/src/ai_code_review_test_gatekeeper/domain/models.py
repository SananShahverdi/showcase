from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

def count_noun(count: int, noun: str) -> str:
    """``1 finding`` / ``2 findings`` for readable report text."""
    return f"{count} {noun}{'' if count == 1 else 's'}"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class Finding(BaseModel):
    tool: str
    rule_id: str
    category: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    end_line: Optional[int] = None
    message: str
    severity: Severity
    remediation: Optional[str] = None
    fingerprint: str = ""

class AnalysisResult(BaseModel):
    findings: List[Finding] = Field(default_factory=list)
    tests_passed: bool = True
    coverage_percent: float = 0.0
    changed_files: List[str] = Field(default_factory=list)
    tool_statuses: Dict[str, str] = Field(default_factory=dict)

class LLMComment(BaseModel):
    file_path: str
    line_range: str
    comment: str
    suggested_fix: Optional[str] = None

class PullRequest(BaseModel):
    id: str
    repo: str
    title: str
    diff_content: str
    base_sha: Optional[str] = None
    head_sha: Optional[str] = None
    reported_coverage_percent: float = Field(default=85.0, ge=0.0, le=100.0)
    reported_tests_passed: bool = True

class ReviewStatus(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    BLOCKED = "blocked"

class ReviewReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    pr_id: str
    repo: str
    title: str = ""
    status: ReviewStatus
    analysis_result: AnalysisResult
    llm_summary: str
    llm_comments: List[LLMComment] = Field(default_factory=list)
    policy_reasons: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DashboardSummary(BaseModel):
    total_reviews: int
    approved: int
    changes_requested: int
    blocked: int
    pass_rate: float
    recurring_rules: Dict[str, int] = Field(default_factory=dict)
