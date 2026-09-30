import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from local_ai_inference_gateway_llmops_console.domain.models import (
    GatewayApiKey,
    GatewayMetrics,
    PromptTemplate,
    ProviderConfig,
    RequestLog,
)


class InMemoryRepository:
    def __init__(self):
        self.providers: Dict[UUID, ProviderConfig] = {}
        self.prompts: Dict[UUID, PromptTemplate] = {}
        self.logs: Dict[UUID, RequestLog] = {}
        self.api_keys: Dict[UUID, GatewayApiKey] = {}
        self.metrics = GatewayMetrics()
        self._rate_windows: Dict[UUID, Tuple[int, float]] = {}

    def save_provider(self, provider: ProviderConfig):
        self.providers[provider.id] = provider

    def get_providers(self) -> List[ProviderConfig]:
        return sorted(self.providers.values(), key=lambda provider: (provider.priority, provider.name))

    def save_prompt(self, prompt: PromptTemplate):
        if prompt.versions and prompt.active_version_id is None:
            prompt.active_version_id = max(prompt.versions, key=lambda version: version.version_number).id
        self.prompts[prompt.id] = prompt

    def get_prompt(self, prompt_id: UUID) -> Optional[PromptTemplate]:
        return self.prompts.get(prompt_id)

    def save_log(self, log: RequestLog, count_request: bool = True):
        self.logs[log.id] = log
        self.metrics.provider_attempts += 1
        if log.error:
            self.metrics.total_errors += 1
        if log.fallback and count_request:
            self.metrics.fallback_requests += 1
        if count_request:
            previous = self.metrics.total_requests
            self.metrics.total_requests += 1
            self.metrics.total_tokens += log.total_tokens
            self.metrics.total_cost += log.cost
            self.metrics.avg_latency_ms = (previous * self.metrics.avg_latency_ms + log.latency_ms) / self.metrics.total_requests

    def get_metrics(self) -> GatewayMetrics:
        return self.metrics

    def get_logs(self) -> List[RequestLog]:
        return sorted(self.logs.values(), key=lambda log: log.timestamp, reverse=True)

    def create_api_key(self, name: str, scopes: List[str], requests_per_minute: int, token_quota: int) -> tuple[GatewayApiKey, str]:
        plain = "lgw_" + secrets.token_urlsafe(24)
        record = GatewayApiKey(
            name=name,
            prefix=plain[:12],
            key_hash=self._hash_key(plain),
            scopes=scopes,
            requests_per_minute=requests_per_minute,
            token_quota=token_quota,
        )
        self.api_keys[record.id] = record
        return record, plain

    def authenticate(self, plain: Optional[str], scope: str) -> Optional[GatewayApiKey]:
        if not self.api_keys:
            return None
        if not plain:
            raise PermissionError("A gateway API key is required")
        digest = self._hash_key(plain)
        key = next((item for item in self.api_keys.values() if hmac.compare_digest(item.key_hash, digest)), None)
        if not key or not key.is_active:
            raise PermissionError("Invalid or revoked gateway API key")
        if scope not in key.scopes:
            raise PermissionError(f"API key does not allow {scope}")
        now = time.monotonic()
        count, start = self._rate_windows.get(key.id, (0, now))
        if now - start >= 60:
            count, start = 0, now
        if count >= key.requests_per_minute:
            raise OverflowError("Request rate limit exceeded")
        self._rate_windows[key.id] = (count + 1, start)
        if key.tokens_used >= key.token_quota:
            raise OverflowError("Token quota exhausted")
        key.last_used_at = datetime.now(timezone.utc)
        return key

    def consume_tokens(self, key: Optional[GatewayApiKey], tokens: int):
        if key:
            if key.tokens_used + tokens > key.token_quota:
                raise OverflowError("Token quota would be exceeded")
            key.tokens_used += tokens

    def reset(self):
        self.__init__()

    @staticmethod
    def _hash_key(plain: str) -> str:
        pepper = os.getenv("GATEWAY_KEY_PEPPER", "local-development-pepper")
        return hmac.new(pepper.encode(), plain.encode(), hashlib.sha256).hexdigest()
