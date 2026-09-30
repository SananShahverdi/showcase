import time
from typing import Dict, List, Tuple

import httpx

from local_ai_inference_gateway_llmops_console.domain.models import ProviderConfig, ProviderType


def _endpoint(base: str, suffix: str) -> str:
    normalized = base.rstrip("/")
    if normalized.endswith(suffix):
        return normalized
    return normalized + suffix


class ProviderAdapters:
    """Real bounded adapters plus a deterministic, explicitly local demo provider."""

    @staticmethod
    def call_chat(provider: ProviderConfig, prompt: str) -> Tuple[str, Dict[str, int], float]:
        if provider.type == ProviderType.MOCK:
            start = time.perf_counter()
            response = f"Deterministic local demo response: {prompt[:160]}"
            return response, ProviderAdapters._estimate_usage(prompt, response), (time.perf_counter() - start) * 1000
        timeout = provider.timeout_ms / 1000
        started = time.perf_counter()
        if provider.type == ProviderType.OLLAMA:
            response = httpx.post(
                _endpoint(provider.api_base, "/api/chat"),
                json={"model": provider.model_name or provider.name, "messages": [{"role": "user", "content": prompt}], "stream": False},
                timeout=timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
            body = response.json()
            content = body["message"]["content"]
            usage = {
                "prompt_tokens": int(body.get("prompt_eval_count", 0)),
                "completion_tokens": int(body.get("eval_count", 0)),
            }
        else:
            headers = {"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}
            response = httpx.post(
                _endpoint(provider.api_base, "/chat/completions"),
                json={"model": provider.model_name or provider.name, "messages": [{"role": "user", "content": prompt}], "stream": False},
                headers=headers,
                timeout=timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            remote_usage = body.get("usage", {})
            usage = {
                "prompt_tokens": int(remote_usage.get("prompt_tokens", 0)),
                "completion_tokens": int(remote_usage.get("completion_tokens", 0)),
            }
        if not any(usage.values()):
            usage = ProviderAdapters._estimate_usage(prompt, content)
        return content, usage, (time.perf_counter() - started) * 1000

    @staticmethod
    def call_embeddings(provider: ProviderConfig, inputs: List[str]) -> Tuple[List[List[float]], Dict[str, int], float]:
        started = time.perf_counter()
        if provider.type == ProviderType.MOCK:
            vectors = [ProviderAdapters._deterministic_vector(text) for text in inputs]
            return vectors, {"prompt_tokens": sum(max(1, len(text) // 4) for text in inputs), "completion_tokens": 0}, (time.perf_counter() - started) * 1000
        timeout = provider.timeout_ms / 1000
        if provider.type == ProviderType.OLLAMA:
            vectors = []
            for text in inputs:
                response = httpx.post(
                    _endpoint(provider.api_base, "/api/embeddings"),
                    json={"model": provider.model_name or provider.name, "prompt": text},
                    timeout=timeout,
                    follow_redirects=False,
                )
                response.raise_for_status()
                vectors.append(response.json()["embedding"])
            usage = {"prompt_tokens": sum(max(1, len(text) // 4) for text in inputs), "completion_tokens": 0}
        else:
            headers = {"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}
            response = httpx.post(
                _endpoint(provider.api_base, "/embeddings"),
                json={"model": provider.model_name or provider.name, "input": inputs},
                headers=headers,
                timeout=timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
            body = response.json()
            vectors = [item["embedding"] for item in body["data"]]
            usage = {"prompt_tokens": int(body.get("usage", {}).get("prompt_tokens", 0)), "completion_tokens": 0}
        return vectors, usage, (time.perf_counter() - started) * 1000

    @staticmethod
    def probe(provider: ProviderConfig) -> tuple[bool, float, str]:
        started = time.perf_counter()
        try:
            url = _endpoint(provider.api_base, "/api/tags") if provider.type == ProviderType.OLLAMA else _endpoint(provider.api_base, "/models")
            if provider.type == ProviderType.MOCK:
                return True, 0.0, "deterministic demo provider"
            headers = {"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}
            response = httpx.get(url, headers=headers, timeout=provider.timeout_ms / 1000, follow_redirects=False)
            response.raise_for_status()
            return True, (time.perf_counter() - started) * 1000, "healthy"
        except Exception as exc:
            return False, (time.perf_counter() - started) * 1000, f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _estimate_usage(prompt: str, response: str) -> Dict[str, int]:
        return {"prompt_tokens": max(1, len(prompt) // 4), "completion_tokens": max(1, len(response) // 4)}

    @staticmethod
    def _deterministic_vector(text: str, dimensions: int = 12) -> List[float]:
        buckets = [0.0] * dimensions
        for index, byte in enumerate(text.encode("utf-8")):
            buckets[index % dimensions] += (byte - 127.5) / 127.5
        magnitude = sum(value * value for value in buckets) ** 0.5 or 1.0
        return [round(value / magnitude, 6) for value in buckets]
