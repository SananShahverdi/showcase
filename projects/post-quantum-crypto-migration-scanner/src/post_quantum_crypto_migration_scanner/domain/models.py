from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingType(str, Enum):
    CODE = "code"
    CONFIG = "config"
    DEPENDENCY = "dependency"
    TLS = "tls"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TLSObservation(BaseModel):
    endpoint: str
    protocol: str
    cipher: Optional[str] = None
    certificate_key_algorithm: Optional[str] = None
    certificate_days_remaining: Optional[int] = None
    key_exchange: Optional[str] = None
    provenance: str = "supplied_observation"


class CryptoFinding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: FindingType
    source: str
    algorithm: str
    severity: Severity
    description: str
    remediation: str
    rule_id: str = "CRYPTO-GENERIC"
    rule_version: str = "2026.1"
    line: Optional[int] = None
    evidence: Optional[str] = None
    confidence: Confidence = Confidence.HIGH
    quantum_vulnerable: bool = False
    migration_priority: int = Field(default=0, ge=0, le=100)


class ScanError(BaseModel):
    service_name: str
    source: str
    code: str
    message: str


class MigrationItem(BaseModel):
    service_name: str
    priority: int = Field(ge=0, le=100)
    finding_ids: List[UUID]
    target_state: str
    rationale: str


class ServiceInventory(BaseModel):
    service_name: str
    findings: List[CryptoFinding]
    is_quantum_safe: bool = False
    posture: str = "unknown"
    retention_years: int = 1
    internet_exposed: bool = False
    algorithm_counts: Dict[str, int] = Field(default_factory=dict)


class ServiceScanInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    files: Dict[str, str] = Field(default_factory=dict)
    endpoints: List[Any] = Field(default_factory=list)
    retention_years: int = Field(default=1, ge=0, le=100)
    internet_exposed: bool = False


class ScanReport(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    rule_version: str = "2026.1"
    scanned_at: datetime = Field(default_factory=utc_now)
    services: List[ServiceInventory]
    migration_plan: List[MigrationItem] = Field(default_factory=list)
    errors: List[ScanError] = Field(default_factory=list)
    total_findings: int
    critical_findings: int
    high_findings: int = 0


class LiveProbeRequest(BaseModel):
    endpoint: str
    authorized: bool = False
    timeout_seconds: float = Field(default=3.0, ge=0.2, le=10.0)


class ScanSummary(BaseModel):
    id: UUID
    rule_version: str
    scanned_at: datetime
    service_count: int
    total_findings: int
    critical_findings: int
    high_findings: int
    error_count: int
