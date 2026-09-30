from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from local_ai_inference_gateway_llmops_console.adapters.provider_adapters import ProviderAdapters
from local_ai_inference_gateway_llmops_console.adapters.repositories import InMemoryRepository
from local_ai_inference_gateway_llmops_console.algorithms.prompt_registry import compile_prompt, extract_variables
from local_ai_inference_gateway_llmops_console.domain.models import GatewayApiKey, GatewayMetrics, PromptTemplate, PromptVersion, ProviderConfig, ProviderType, RequestLog
from local_ai_inference_gateway_llmops_console.services.gateway_service import GatewayService, ModelNotFoundError

router = APIRouter()
openai_router = APIRouter()
repo = InMemoryRepository()
service = GatewayService(repo)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str = Field(min_length=1, max_length=100_000)


class ChatCompletionRequest(BaseModel):
    model: str = "default"
    messages: List[ChatMessage]
    stream: bool = False
    requires_high_privacy: bool = False
    redact_pii: bool = False
    template_id: Optional[UUID] = None
    template_vars: Optional[Dict[str, Any]] = None


class EmbeddingRequest(BaseModel):
    model: str = "default"
    input: Union[str, List[str]]
    requires_high_privacy: bool = False
    redact_pii: bool = False


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["chat", "embeddings"])
    requests_per_minute: int = Field(default=60, ge=1, le=10_000)
    token_quota: int = Field(default=100_000, ge=1)


class PromptVersionCreate(BaseModel):
    template_string: str = Field(min_length=1, max_length=100_000)


def _bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, separator, value = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not value:
        raise HTTPException(status_code=401, detail="Authorization must use Bearer scheme")
    return value


def _authenticate(authorization: Optional[str], scope: str) -> Optional[GatewayApiKey]:
    try:
        return repo.authenticate(_bearer(authorization), scope)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


def _chat(request: ChatCompletionRequest, authorization: Optional[str]):
    if request.stream:
        raise HTTPException(status_code=400, detail="stream=true is not enabled by this local build")
    key = _authenticate(authorization, "chat")
    prompt = "\n".join(message.content for message in request.messages)
    if request.template_id:
        template = repo.get_prompt(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        try:
            prompt = compile_prompt(template, request.template_vars or {})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not prompt.strip():
        raise HTTPException(status_code=422, detail="At least one message or a template is required")
    try:
        return service.handle_chat_completion(prompt, request.requires_high_privacy, key, request.redact_pii, request.model)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@openai_router.post("/chat/completions")
def chat_completions(request: ChatCompletionRequest, authorization: Optional[str] = Header(None)):
    return _chat(request, authorization)


@router.post("/v1/chat/completions", deprecated=True)
def compatibility_chat(request: ChatCompletionRequest, authorization: Optional[str] = Header(None)):
    return _chat(request, authorization)


def _embedding(request: EmbeddingRequest, authorization: Optional[str]):
    key = _authenticate(authorization, "embeddings")
    inputs = [request.input] if isinstance(request.input, str) else request.input
    if not inputs or any(not item.strip() for item in inputs):
        raise HTTPException(status_code=422, detail="Embedding input cannot be empty")
    try:
        return service.handle_embeddings(inputs, request.requires_high_privacy, key, request.redact_pii, request.model)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@openai_router.post("/embeddings")
def embeddings(request: EmbeddingRequest, authorization: Optional[str] = Header(None)):
    return _embedding(request, authorization)


@router.post("/v1/embeddings", deprecated=True)
def compatibility_embeddings(request: EmbeddingRequest, authorization: Optional[str] = Header(None)):
    return _embedding(request, authorization)


@openai_router.get("/models")
def models():
    data = [{"id": provider.model_name or provider.name, "object": "model", "owned_by": provider.name} for provider in repo.get_providers() if provider.is_active]
    return {"object": "list", "data": data}


@router.post("/admin/providers", response_model=ProviderConfig)
def add_provider(provider: ProviderConfig):
    repo.save_provider(provider)
    return provider


@router.get("/admin/providers", response_model=List[ProviderConfig])
def list_providers():
    return repo.get_providers()


@router.post("/admin/providers/{provider_id}/probe")
def probe_provider(provider_id: UUID):
    provider = repo.providers.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    healthy, latency_ms, detail = ProviderAdapters.probe(provider)
    provider.health_status = "healthy" if healthy else "unhealthy"
    repo.save_provider(provider)
    return {"healthy": healthy, "latency_ms": latency_ms, "detail": detail}


@router.post("/admin/keys")
def create_api_key(request: ApiKeyCreate):
    invalid = set(request.scopes) - {"chat", "embeddings"}
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unknown scopes: {', '.join(sorted(invalid))}")
    key, plain = repo.create_api_key(request.name, request.scopes, request.requests_per_minute, request.token_quota)
    public = key.model_dump(mode="json", exclude={"key_hash"})
    return {**public, "key": plain, "warning": "This value is shown once; store it securely."}


@router.get("/admin/keys")
def list_api_keys():
    return [key.model_dump(mode="json", exclude={"key_hash"}) for key in repo.api_keys.values()]


@router.post("/admin/templates", response_model=PromptTemplate)
def add_template(template: PromptTemplate):
    for version in template.versions:
        derived = extract_variables(version.template_string)
        if sorted(derived) != sorted(version.variables):
            raise HTTPException(status_code=422, detail="Declared template variables do not match the template")
    repo.save_prompt(template)
    return template


@router.get("/admin/templates", response_model=List[PromptTemplate])
def list_templates():
    return list(repo.prompts.values())


@router.post("/admin/templates/{template_id}/versions", response_model=PromptTemplate)
def add_prompt_version(template_id: UUID, request: PromptVersionCreate):
    template = repo.get_prompt(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    number = max((version.version_number for version in template.versions), default=0) + 1
    template.versions.append(PromptVersion(version_number=number, template_string=request.template_string, variables=extract_variables(request.template_string)))
    repo.save_prompt(template)
    return template


@router.post("/admin/templates/{template_id}/activate/{version_id}", response_model=PromptTemplate)
def activate_prompt_version(template_id: UUID, version_id: UUID):
    template = repo.get_prompt(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not any(version.id == version_id for version in template.versions):
        raise HTTPException(status_code=404, detail="Prompt version not found")
    template.active_version_id = version_id
    repo.save_prompt(template)
    return template


@router.get("/admin/metrics", response_model=GatewayMetrics)
def get_metrics():
    return repo.get_metrics()


@router.get("/admin/logs", response_model=List[RequestLog])
def get_logs():
    return repo.get_logs()


@router.post("/demo/seed")
def seed_demo():
    repo.reset()
    provider = ProviderConfig(name="deterministic-local", type=ProviderType.MOCK, api_base="inprocess://demo", priority=1, privacy_level="high", health_status="healthy")
    repo.save_provider(provider)
    version = PromptVersion(version_number=1, template_string="Summarize for {audience}: {text}", variables=["audience", "text"])
    template = PromptTemplate(name="Audience summary", description="Seeded strict template", versions=[version], active_version_id=version.id)
    repo.save_prompt(template)
    key, plain = repo.create_api_key("local-demo", ["chat", "embeddings"], 60, 10_000)
    return {"provider": provider, "template": template, "api_key": {**key.model_dump(mode="json", exclude={"key_hash"}), "key": plain}}
