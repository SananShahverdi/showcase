from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PluginStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class VersionStatus(str, Enum):
    VALIDATED = "validated"
    QUARANTINED = "quarantined"


class RuntimeKind(str, Enum):
    WASM = "wasm"
    LOCAL_ADAPTER = "local_adapter"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    TRAP = "trap"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    OUTPUT_LIMIT = "output_limit"


class ResourceLimits(BaseModel):
    max_memory_mb: int = Field(default=64, ge=1, le=512)
    timeout_ms: int = Field(default=50, ge=1, le=10_000)
    fuel: int = Field(default=100_000, ge=1_000, le=100_000_000)
    max_input_bytes: int = Field(default=64_000, ge=1, le=1_000_000)
    max_output_bytes: int = Field(default=64_000, ge=1, le=1_000_000)


class PluginManifest(BaseModel):
    abi_version: str = "edge-json-v1"
    runtime_kind: RuntimeKind = RuntimeKind.WASM
    entrypoint: str = "run"
    allowed_imports: List[str] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    output_schema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    local_adapter: Optional[str] = None


class ValidationFinding(BaseModel):
    code: str
    message: str
    blocking: bool = True


class PluginVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    plugin_id: str
    version_tag: str
    artifact: str
    artifact_sha256: str
    artifact_size_bytes: int
    manifest: PluginManifest
    status: VersionStatus
    validation_findings: List[ValidationFinding] = Field(default_factory=list)
    canary_passed: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def wasm_base64(self) -> Optional[str]:
        return self.artifact if self.manifest.runtime_kind == RuntimeKind.WASM else None


class ActivationRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    plugin_id: str
    from_version_id: Optional[UUID] = None
    to_version_id: UUID
    action: str
    actor: str
    created_at: datetime = Field(default_factory=utc_now)


class Plugin(BaseModel):
    id: str
    name: str
    description: str
    active_version_id: Optional[UUID] = None
    limits: ResourceLimits = Field(default_factory=ResourceLimits)
    versions: List[PluginVersion] = Field(default_factory=list)
    activation_history: List[ActivationRecord] = Field(default_factory=list)


class VersionUpload(BaseModel):
    version_tag: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    wasm_base64: Optional[str] = None
    manifest: PluginManifest = Field(default_factory=PluginManifest)


class ActivationRequest(BaseModel):
    actor: str = Field(default="local-operator", min_length=1, max_length=120)
    expected_active_version: Optional[str] = None


class ExecutionRequest(BaseModel):
    plugin_id: str
    payload: Dict[str, Any]
    version_tag: Optional[str] = None


class ExecutionResult(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    plugin_id: str
    version_tag: str
    artifact_sha256: str
    runtime_kind: RuntimeKind
    runtime_provenance: str
    input_sha256: str
    status: ExecutionStatus
    output_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    latency_ms: float
    fuel_consumed: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now)


class PluginMetrics(BaseModel):
    plugin_id: str
    version_tag: str
    executions: int
    errors: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float


class BenchmarkReport(BaseModel):
    plugin_id: str
    version_tag: str
    runtime_kind: RuntimeKind
    label: str
    iterations: int
    average_latency_ms: float
    p95_latency_ms: float
