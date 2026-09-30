from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScenarioType(str, Enum):
    DIRECT_INJECTION = "direct_injection"
    INDIRECT_INJECTION = "indirect_injection"
    INSECURE_OUTPUT = "insecure_output"
    DATA_LEAKAGE = "data_leakage"
    EXCESSIVE_AGENCY = "excessive_agency"
    WEAK_TOOL_PERMISSIONS = "weak_tool_permissions"


class AppMode(str, Enum):
    VULNERABLE = "vulnerable"
    HARDENED = "hardened"


class UserRole(str, Enum):
    LEARNER = "learner"
    DEVELOPER = "developer"
    SECURITY_ADMIN = "security_admin"


class DecisionEffect(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"
    SANITIZE = "sanitize"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CONSUMED = "consumed"


class SecurityDecision(BaseModel):
    control_id: str
    effect: DecisionEffect
    reason: str


class ExecuteRequest(BaseModel):
    mode: AppMode
    payload: Optional[str] = Field(default=None, max_length=8_000)
    role: UserRole = UserRole.LEARNER


class ExecutionResult(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    query: str
    mode: AppMode
    scenario_type: ScenarioType
    role: UserRole = UserRole.LEARNER
    was_successful_attack: bool
    tools_called: List[str] = Field(default_factory=list)
    requested_tools: List[str] = Field(default_factory=list)
    output: str
    error: Optional[str] = None
    mitigation_triggered: bool = False
    controls_triggered: List[str] = Field(default_factory=list)
    decisions: List[SecurityDecision] = Field(default_factory=list)
    approval_id: Optional[UUID] = None
    synthetic_effect: Optional[str] = None
    expected_outcome_met: bool = True
    duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)


class Scenario(BaseModel):
    id: str
    version: str = "1.0"
    type: ScenarioType
    name: str
    description: str
    attack_payload: str
    mitigation_description: str
    threat: str
    expected_vulnerable: str
    expected_hardened: str
    allowed_tools_by_role: Dict[UserRole, List[str]] = Field(default_factory=dict)


class Approval(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    scenario_id: str
    requested_action: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: UserRole
    resolved_by: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    consumed_at: Optional[datetime] = None


class ApprovalDecision(BaseModel):
    approve: bool
    actor: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=3, max_length=500)


class SecurityReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    policy_version: str = "2026.1"
    scenarios_tested: int
    vulnerabilities_found: int
    mitigations_verified: int
    mitigation_rate: float
    results: List[ExecutionResult]
    created_at: datetime = Field(default_factory=utc_now)


class MetricsSummary(BaseModel):
    total_runs: int
    blocked_runs: int
    successful_attacks: int
    pending_approvals: int
    average_duration_ms: float
