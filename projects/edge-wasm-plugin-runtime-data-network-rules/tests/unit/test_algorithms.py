import base64

from edge_wasm_plugin_runtime.algorithms.runtime_host import RuntimeHost, WasmValidator
from edge_wasm_plugin_runtime.domain.models import (
    ExecutionStatus, PluginManifest, ResourceLimits, RuntimeKind,
)


def adapter_manifest(name: str) -> PluginManifest:
    return PluginManifest(runtime_kind=RuntimeKind.LOCAL_ADAPTER, local_adapter=name)


def test_data_cleaning_adapter_execution_is_explicitly_labeled():
    payload = {"data": " DIRTY DATA ", "action": "clean"}
    output, status, error, latency, provenance, _ = RuntimeHost.execute(
        RuntimeKind.LOCAL_ADAPTER, "adapter://data-cleaner", adapter_manifest("data-cleaner"), payload, ResourceLimits()
    )
    assert status == ExecutionStatus.SUCCESS
    assert output["data"] == "dirty data"
    assert provenance == "trusted-python-adapter-v1"


def test_alert_filter_adapter_and_output_limit():
    payload = {"severity": "low"}
    output, status, error, _, _, _ = RuntimeHost.execute(
        RuntimeKind.LOCAL_ADAPTER, "adapter://alert-filter", adapter_manifest("alert-filter"), payload, ResourceLimits()
    )
    assert status == ExecutionStatus.SUCCESS
    assert output["drop"] is True

    output, status, error, _, _, _ = RuntimeHost.execute(
        RuntimeKind.LOCAL_ADAPTER, "adapter://alert-filter", adapter_manifest("alert-filter"), payload,
        ResourceLimits(max_output_bytes=1),
    )
    assert status == ExecutionStatus.OUTPUT_LIMIT
    assert output == {}


def test_wasm_validation_rejects_fake_strings_and_checks_exports():
    try:
        WasmValidator.decode("mock-route-wasm-binary-string")
    except ValueError as exc:
        assert "strict base64" in str(exc)
    else:
        raise AssertionError("non-base64 input must be rejected")

    minimal = base64.b64encode(b"\x00asm\x01\x00\x00\x00").decode()
    _, findings = WasmValidator.validate(minimal, PluginManifest())
    assert [finding.code for finding in findings] == ["missing_entrypoint"]


def test_missing_runtime_never_falls_back_to_local_rule_logic(monkeypatch):
    monkeypatch.setattr(RuntimeHost, "runtime_available", staticmethod(lambda: False))
    manifest = PluginManifest(runtime_kind=RuntimeKind.WASM)
    _, status, error, _, provenance, _ = RuntimeHost.execute(
        RuntimeKind.WASM, "AGFzbQEAAAA=", manifest, {"action": "route", "region": "EU"}, ResourceLimits()
    )
    assert status == ExecutionStatus.RUNTIME_UNAVAILABLE
    assert "adapter" not in provenance
    assert error
