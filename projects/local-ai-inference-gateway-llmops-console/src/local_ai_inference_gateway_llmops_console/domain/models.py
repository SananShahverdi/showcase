from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum

class ProviderType(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    OPENAI = "openai"
    MOCK = "mock"

class ProviderConfig(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    type: ProviderType
    api_base: str
    api_key: Optional[str] = Field(default=None, exclude=True)
    model_name: Optional[str] = None
    priority: int = 1 # Lower is higher priority
    is_active: bool = True
    capabilities: List[str] = Field(default_factory=lambda: ["chat", "embeddings"])
    cost_per_1k_tokens: float = 0.0
    privacy_level: str = "high" # high, medium, low
    timeout_ms: int = 15_000
    health_status: str = "unknown"

    # `model_name` is an external provider field, not a Pydantic method namespace.
    model_config = {"protected_namespaces": ()}

class PromptVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    version_number: int
    template_string: str
    variables: List[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PromptTemplate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    versions: List[PromptVersion] = Field(default_factory=list)
    active_version_id: Optional[UUID] = None

class RequestLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str
    provider_id: UUID
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    error: bool = False
    error_message: Optional[str] = None
    error_class: Optional[str] = None
    attempt: int = 1
    fallback: bool = False
    capability: str = "chat"
    cost: float = 0.0
    api_key_prefix: Optional[str] = None
    
    model_config = {"protected_namespaces": ()}

class GatewayMetrics(BaseModel):
    total_requests: int = 0
    total_errors: int = 0
    provider_attempts: int = 0
    fallback_requests: int = 0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0


class GatewayApiKey(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    prefix: str
    key_hash: str
    scopes: List[str] = Field(default_factory=lambda: ["chat", "embeddings"])
    requests_per_minute: int = 60
    token_quota: int = 100_000
    tokens_used: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
