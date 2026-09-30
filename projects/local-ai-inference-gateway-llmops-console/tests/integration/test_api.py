from fastapi.testclient import TestClient
import pytest

from local_ai_inference_gateway_llmops_console.adapters.provider_adapters import ProviderAdapters
from local_ai_inference_gateway_llmops_console.api.app import app
from local_ai_inference_gateway_llmops_console.api.routes import repo
from local_ai_inference_gateway_llmops_console.domain.models import ProviderType

client = TestClient(app)


def test_key_chat_embedding_prompt_and_metrics():
    seeded = client.post("/api/demo/seed")
    assert seeded.status_code == 200
    key = seeded.json()["api_key"]["key"]
    headers = {"Authorization": f"Bearer {key}"}
    chat = client.post("/v1/chat/completions", headers=headers, json={
        "messages": [{"role": "user", "content": "Contact alice@example.com"}],
        "requires_high_privacy": True, "redact_pii": True,
    })
    assert chat.status_code == 200
    assert chat.json()["object"] == "chat.completion"
    assert "[REDACTED_EMAIL]" in chat.json()["choices"][0]["message"]["content"]

    embedding = client.post("/v1/embeddings", headers=headers, json={"input": ["alpha", "beta"], "requires_high_privacy": True})
    assert embedding.status_code == 200
    assert len(embedding.json()["data"]) == 2
    assert len(embedding.json()["data"][0]["embedding"]) == 12
    assert client.get("/v1/models").json()["data"]
    assert client.get("/api/admin/templates").json()[0]["active_version_id"]
    metrics = client.get("/api/admin/metrics").json()
    assert metrics["total_requests"] == 2
    assert metrics["provider_attempts"] == 2
    logs = client.get("/api/admin/logs").json()
    assert all("api_key_used" not in log for log in logs)
    assert all(log["api_key_prefix"] for log in logs)


def test_failed_primary_is_logged_before_safe_fallback(monkeypatch):
    seeded = client.post("/api/demo/seed").json()
    key = seeded["api_key"]["key"]
    primary = client.post("/api/admin/providers", json={
        "name": "unavailable-primary", "type": "openai", "api_base": "https://provider.invalid/v1",
        "priority": 0, "privacy_level": "high", "timeout_ms": 100,
    })
    assert primary.status_code == 200
    original = ProviderAdapters.call_chat

    def controlled(provider, prompt):
        if provider.type == ProviderType.OPENAI:
            raise TimeoutError("contract timeout")
        return original(provider, prompt)

    monkeypatch.setattr(ProviderAdapters, "call_chat", controlled)
    response = client.post("/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={
        "messages": [{"role": "user", "content": "hello"}], "requires_high_privacy": True,
    })
    assert response.status_code == 200
    assert response.json()["fallback"] is True
    logs = client.get("/api/admin/logs").json()
    attempts = [log for log in logs if log["request_id"] == response.json()["id"]]
    assert [attempt["error"] for attempt in sorted(attempts, key=lambda item: item["attempt"])] == [True, False]
    assert client.get("/api/admin/metrics").json()["fallback_requests"] == 1


@pytest.mark.parametrize(("path", "payload"), [
    ("/v1/chat/completions", {"messages": [{"role": "user", "content": "hello"}]}),
    ("/v1/embeddings", {"input": "hello"}),
])
def test_explicit_model_selects_matching_provider_and_missing_model_is_rejected(path, payload):
    seeded = client.post("/api/demo/seed").json()
    headers = {"Authorization": f"Bearer {seeded['api_key']['key']}"}
    created = client.post("/api/admin/providers", json={
        "name": "specific-provider", "model_name": "specific-model", "type": "mock",
        "api_base": "inprocess://specific", "priority": 99,
    })
    assert created.status_code == 200
    response = client.post(path, headers=headers, json={**payload, "model": "specific-model"})
    assert response.status_code == 200
    assert response.json()["model"] == "specific-model"
    assert response.json()["provider"] == "specific-provider"
    missing = client.post(path, headers=headers, json={**payload, "model": "not-registered"})
    assert missing.status_code == 404
    assert "not-registered" in missing.json()["detail"]
    assert client.get("/api/admin/metrics").json()["provider_attempts"] == 1
