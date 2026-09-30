from uuid import uuid4
from local_ai_inference_gateway_llmops_console.domain.models import ProviderConfig, ProviderType, PromptTemplate, PromptVersion
from local_ai_inference_gateway_llmops_console.algorithms.routing_policy import select_provider
from local_ai_inference_gateway_llmops_console.algorithms.prompt_registry import extract_variables, compile_prompt
from local_ai_inference_gateway_llmops_console.adapters.repositories import InMemoryRepository
from local_ai_inference_gateway_llmops_console.services.gateway_service import GatewayService

def test_routing_policy():
    p1 = ProviderConfig(name="ollama1", type=ProviderType.OLLAMA, api_base="url", priority=2, privacy_level="high")
    p2 = ProviderConfig(name="openai1", type=ProviderType.OPENAI, api_base="url", priority=1, privacy_level="low")
    p3 = ProviderConfig(name="mock1", type=ProviderType.MOCK, api_base="url", priority=3, privacy_level="high")
    
    providers = [p1, p2, p3]
    
    # Priority 1 is OpenAI (low privacy)
    selected = select_provider(providers, "chat", False)
    assert selected.name == "openai1"
    
    # Needs high privacy, so skips OpenAI, next priority is Ollama
    selected_privacy = select_provider(providers, "chat", True)
    assert selected_privacy.name == "ollama1"

def test_prompt_registry():
    vars_found = extract_variables("Hello {user}, your role is {role}.")
    assert vars_found == ["user", "role"]
    
    version = PromptVersion(version_number=1, template_string="Hello {name}", variables=["name"])
    template = PromptTemplate(name="Greeting", description="A greeting", versions=[version], active_version_id=version.id)
    
    compiled = compile_prompt(template, {"name": "Alice"})
    assert compiled == "Hello Alice"


def test_hashed_scoped_key_quota_and_redaction():
    repo = InMemoryRepository()
    record, plain = repo.create_api_key("test", ["chat"], requests_per_minute=2, token_quota=5)
    assert plain not in record.key_hash
    assert repo.authenticate(plain, "chat").id == record.id
    try:
        repo.authenticate(plain, "embeddings")
        assert False, "scope check should fail"
    except PermissionError:
        pass
    repo.consume_tokens(record, 5)
    try:
        repo.consume_tokens(record, 1)
        assert False, "quota check should fail"
    except OverflowError:
        pass
    assert GatewayService.redact("Email me at alice@example.com or +1 555 123 4567") == "Email me at [REDACTED_EMAIL] or [REDACTED_PHONE]"
