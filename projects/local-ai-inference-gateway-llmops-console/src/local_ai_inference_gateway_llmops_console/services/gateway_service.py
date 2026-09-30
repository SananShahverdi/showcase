import re
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from local_ai_inference_gateway_llmops_console.adapters.provider_adapters import ProviderAdapters
from local_ai_inference_gateway_llmops_console.adapters.repositories import InMemoryRepository
from local_ai_inference_gateway_llmops_console.algorithms.routing_policy import select_provider
from local_ai_inference_gateway_llmops_console.domain.models import GatewayApiKey, ProviderConfig, RequestLog


class ModelNotFoundError(ValueError):
    pass


class GatewayService:
    def __init__(self, repo: InMemoryRepository):
        self.repo = repo

    def handle_chat_completion(
        self,
        prompt: str,
        requires_high_privacy: bool = False,
        gateway_key: Optional[GatewayApiKey] = None,
        redact_pii: bool = False,
        model: str = "default",
    ) -> Dict[str, Any]:
        safe_prompt = self.redact(prompt) if redact_pii else prompt
        request_id = f"chatcmpl-{uuid4().hex}"
        content, usage, latency, provider, fallback = self._execute_with_fallback(
            request_id, "chat", safe_prompt, requires_high_privacy, gateway_key, model
        )
        total_tokens = usage["prompt_tokens"] + usage["completion_tokens"]
        self.repo.consume_tokens(gateway_key, total_tokens)
        return {
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": provider.model_name or provider.name,
            "provider": provider.name,
            "fallback": fallback,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {**usage, "total_tokens": total_tokens},
        }

    def handle_embeddings(
        self,
        inputs: List[str],
        requires_high_privacy: bool = False,
        gateway_key: Optional[GatewayApiKey] = None,
        redact_pii: bool = False,
        model: str = "default",
    ) -> Dict[str, Any]:
        normalized = [self.redact(value) if redact_pii else value for value in inputs]
        request_id = f"embd-{uuid4().hex}"
        vectors, usage, latency, provider, fallback = self._execute_embeddings_with_fallback(
            request_id, normalized, requires_high_privacy, gateway_key, model
        )
        total_tokens = usage["prompt_tokens"]
        self.repo.consume_tokens(gateway_key, total_tokens)
        return {
            "object": "list",
            "model": provider.model_name or provider.name,
            "provider": provider.name,
            "fallback": fallback,
            "data": [{"object": "embedding", "index": index, "embedding": vector} for index, vector in enumerate(vectors)],
            "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
            "request_id": request_id,
        }

    def _providers_for_model(self, model: str) -> List[ProviderConfig]:
        providers = self.repo.get_providers()
        if model == "default":
            return providers
        matches = [provider for provider in providers if provider.is_active and (provider.model_name or provider.name) == model]
        if not matches:
            raise ModelNotFoundError(f"No active provider serves model '{model}'")
        return matches

    def _execute_with_fallback(
        self,
        request_id: str,
        capability: str,
        prompt: str,
        privacy: bool,
        gateway_key: Optional[GatewayApiKey],
        model: str = "default",
    ) -> Tuple[str, Dict[str, int], float, ProviderConfig, bool]:
        remaining = self._providers_for_model(model)
        attempt = 0
        last_error = "No eligible provider found"
        while remaining:
            provider = select_provider(remaining, capability, privacy)
            if not provider:
                break
            attempt += 1
            started = time.perf_counter()
            try:
                content, usage, latency = ProviderAdapters.call_chat(provider, prompt)
                self._log(request_id, provider, capability, usage, latency, gateway_key, attempt, attempt > 1)
                return content, usage, latency, provider, attempt > 1
            except Exception as exc:
                latency = (time.perf_counter() - started) * 1000
                last_error = f"{type(exc).__name__}: {exc}"
                remaining = [item for item in remaining if item.id != provider.id]
                has_fallback = select_provider(remaining, capability, privacy) is not None
                self._log(
                    request_id,
                    provider,
                    capability,
                    {"prompt_tokens": 0, "completion_tokens": 0},
                    latency,
                    gateway_key,
                    attempt,
                    attempt > 1,
                    error=last_error,
                    count_request=not has_fallback,
                )
        raise RuntimeError(f"Inference failed after {attempt} provider attempt(s): {last_error}")

    def _execute_embeddings_with_fallback(
        self,
        request_id: str,
        inputs: List[str],
        privacy: bool,
        gateway_key: Optional[GatewayApiKey],
        model: str = "default",
    ) -> Tuple[List[List[float]], Dict[str, int], float, ProviderConfig, bool]:
        remaining = self._providers_for_model(model)
        attempt = 0
        last_error = "No eligible provider found"
        while remaining:
            provider = select_provider(remaining, "embeddings", privacy)
            if not provider:
                break
            attempt += 1
            started = time.perf_counter()
            try:
                vectors, usage, latency = ProviderAdapters.call_embeddings(provider, inputs)
                self._log(request_id, provider, "embeddings", usage, latency, gateway_key, attempt, attempt > 1)
                return vectors, usage, latency, provider, attempt > 1
            except Exception as exc:
                latency = (time.perf_counter() - started) * 1000
                last_error = f"{type(exc).__name__}: {exc}"
                remaining = [item for item in remaining if item.id != provider.id]
                has_fallback = select_provider(remaining, "embeddings", privacy) is not None
                self._log(request_id, provider, "embeddings", {"prompt_tokens": 0, "completion_tokens": 0}, latency, gateway_key, attempt, attempt > 1, last_error, not has_fallback)
        raise RuntimeError(f"Embedding failed after {attempt} provider attempt(s): {last_error}")

    def _log(
        self,
        request_id: str,
        provider: ProviderConfig,
        capability: str,
        usage: Dict[str, int],
        latency: float,
        gateway_key: Optional[GatewayApiKey],
        attempt: int,
        fallback: bool,
        error: Optional[str] = None,
        count_request: bool = True,
    ):
        total = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        self.repo.save_log(
            RequestLog(
                request_id=request_id,
                provider_id=provider.id,
                model_name=provider.model_name or provider.name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=total,
                latency_ms=latency,
                error=error is not None,
                error_message=error,
                error_class=error.split(":", 1)[0] if error else None,
                attempt=attempt,
                fallback=fallback,
                capability=capability,
                cost=(total / 1000) * provider.cost_per_1k_tokens,
                api_key_prefix=gateway_key.prefix if gateway_key else None,
            ),
            count_request=count_request,
        )

    @staticmethod
    def redact(text: str) -> str:
        text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]", text, flags=re.I)
        return re.sub(r"(?<!\w)(?:\+?\d[\d .()-]{7,}\d)", "[REDACTED_PHONE]", text)
