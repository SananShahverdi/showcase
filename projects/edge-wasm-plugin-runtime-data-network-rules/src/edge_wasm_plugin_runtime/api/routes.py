from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from edge_wasm_plugin_runtime.adapters.repositories import PluginRepository
from edge_wasm_plugin_runtime.algorithms.runtime_host import ALLOWED_ADAPTERS, RuntimeHost
from edge_wasm_plugin_runtime.domain.models import (
    ActivationRequest, BenchmarkReport, ExecutionRequest, ExecutionResult, Plugin, PluginManifest,
    PluginMetrics, PluginVersion, RuntimeKind, VersionUpload,
)
from edge_wasm_plugin_runtime.services.plugin_service import PluginService

router = APIRouter()
repo = PluginRepository()
service = PluginService(repo)


class CanaryPayload(BaseModel):
    payload: Dict[str, Any]


class BenchmarkPayload(BaseModel):
    payload: Dict[str, Any]
    iterations: int = Field(default=25, ge=1, le=500)


def not_found_or_conflict(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(exc).lower() else 409, detail=str(exc))


@router.get("/plugins", response_model=List[Plugin])
def list_plugins() -> List[Plugin]:
    return repo.get_all()


@router.get("/plugins/{plugin_id}", response_model=Plugin)
def get_plugin(plugin_id: str) -> Plugin:
    plugin = repo.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin


@router.post("/plugins/{plugin_id}", response_model=Plugin)
def register_plugin(plugin_id: str, name: str, description: str) -> Plugin:
    try:
        return service.register_plugin(plugin_id, name, description)
    except ValueError as exc:
        raise not_found_or_conflict(exc) from exc


@router.post("/plugins/{plugin_id}/versions", response_model=PluginVersion)
def upload_version(plugin_id: str, payload: VersionUpload) -> PluginVersion:
    try:
        return service.upload_version(plugin_id, payload.version_tag, payload.wasm_base64, payload.manifest)
    except ValueError as exc:
        raise not_found_or_conflict(exc) from exc


@router.post("/plugins/{plugin_id}/versions/{version_tag}/canary", response_model=ExecutionResult)
def canary(plugin_id: str, version_tag: str, payload: CanaryPayload) -> ExecutionResult:
    try:
        return service.canary(plugin_id, version_tag, payload.payload)
    except ValueError as exc:
        raise not_found_or_conflict(exc) from exc


@router.post("/plugins/{plugin_id}/activate/{version_tag}", response_model=Plugin)
def activate_version(plugin_id: str, version_tag: str, request: ActivationRequest | None = None) -> Plugin:
    request = request or ActivationRequest()
    try:
        return service.activate_version(plugin_id, version_tag, request.actor, request.expected_active_version)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise not_found_or_conflict(exc) from exc


@router.post("/plugins/{plugin_id}/rollback", response_model=Plugin)
def rollback(plugin_id: str, actor: str = "local-operator") -> Plugin:
    try:
        return service.rollback(plugin_id, actor)
    except ValueError as exc:
        raise not_found_or_conflict(exc) from exc


@router.post("/execute", response_model=ExecutionResult)
def execute_plugin(request: ExecutionRequest) -> ExecutionResult:
    try:
        return service.execute(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plugins/{plugin_id}/executions", response_model=List[ExecutionResult])
def execution_history(plugin_id: str, limit: int = Query(default=100, ge=1, le=500)) -> List[ExecutionResult]:
    try:
        return service.history(plugin_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/plugins/{plugin_id}/versions/{version_tag}/metrics", response_model=PluginMetrics)
def metrics(plugin_id: str, version_tag: str) -> PluginMetrics:
    try:
        return service.metrics(plugin_id, version_tag)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plugins/{plugin_id}/versions/{version_tag}/benchmark", response_model=BenchmarkReport)
def benchmark(plugin_id: str, version_tag: str, payload: BenchmarkPayload) -> BenchmarkReport:
    try:
        return service.benchmark(plugin_id, version_tag, payload.payload, payload.iterations)
    except ValueError as exc:
        raise not_found_or_conflict(exc) from exc


@router.get("/runtime/capabilities")
def runtime_capabilities():
    return {
        "abi_version": "edge-json-v1",
        "wasmtime_available": RuntimeHost.runtime_available(),
        "wasm_execution_ready": RuntimeHost.runtime_available(),
        "abi": {
            "memory": "exported 32-bit linear memory",
            "alloc": "alloc(i32 input_length) -> i32 input_pointer",
            "run": "run(i32 input_pointer, i32 input_length) -> i64 (output_pointer << 32 | output_length)",
            "encoding": "UTF-8 JSON object",
        },
        "limits_enforced": ["fuel", "linear_memory", "execution_timeout", "input_bytes", "output_bytes"],
        "trusted_local_adapters": sorted(ALLOWED_ADAPTERS),
        "default_capabilities": [],
    }


@router.get("/runtime/examples")
def runtime_examples():
    from edge_wasm_plugin_runtime.algorithms.wasm_examples import JSON_NORMALIZER_WAT, json_normalizer_artifact
    return [{
        "id": "json-normalizer",
        "description": "Real Wasm normalizes ASCII uppercase letters in JSON keys and string values",
        "wat": JSON_NORMALIZER_WAT,
        "wasm_base64": json_normalizer_artifact() if RuntimeHost.runtime_available() else None,
        "manifest": PluginManifest(runtime_kind=RuntimeKind.WASM),
    }]


@router.post("/demo/seed", response_model=List[Plugin])
def seed_demo() -> List[Plugin]:
    examples = [
        ("data-cleaner", "Data cleaner", "Normalizes string fields"),
        ("alert-filter", "Alert filter", "Suppresses low-severity alerts"),
        ("routing-policy", "Routing policy", "Selects a regional route"),
    ]
    for plugin_id, name, description in examples:
        plugin = repo.get_plugin(plugin_id)
        if plugin is None:
            plugin = service.register_plugin(plugin_id, name, description)
            manifest = PluginManifest(runtime_kind=RuntimeKind.LOCAL_ADAPTER, local_adapter=plugin_id)
            service.upload_version(plugin_id, "1.0.0", None, manifest)
            service.canary(plugin_id, "1.0.0", {"value": " Demo ", "severity": "low", "region": "EU"})
            service.activate_version(plugin_id, "1.0.0", "demo-seeder")
    if RuntimeHost.runtime_available() and repo.get_plugin("json-normalizer") is None:
        from edge_wasm_plugin_runtime.algorithms.wasm_examples import json_normalizer_artifact
        service.register_plugin("json-normalizer", "Wasm JSON normalizer", "Real WebAssembly lowercases ASCII letters in JSON keys and values")
        service.upload_version("json-normalizer", "1.0.0", json_normalizer_artifact(), PluginManifest())
        result = service.canary("json-normalizer", "1.0.0", {"message": "HELLO FROM WASM"})
        if result.status.value == "success":
            service.activate_version("json-normalizer", "1.0.0", "demo-seeder")
    return repo.get_all()
