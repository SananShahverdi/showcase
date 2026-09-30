import base64
from pathlib import Path

import pytest
import wasmtime

from edge_wasm_plugin_runtime.algorithms.runtime_host import RuntimeHost, WasmValidator
from edge_wasm_plugin_runtime.domain.models import ExecutionStatus, PluginManifest, ResourceLimits, RuntimeKind


def encode(wat: str) -> str:
    return base64.b64encode(wasmtime.wat2wasm(wat)).decode()


def module(run_body: str, *, pages: int = 1, alloc_body: str = "i32.const 0") -> str:
    return encode(f'''(module
      (memory (export "memory") {pages})
      (func (export "alloc") (param i32) (result i32) {alloc_body})
      (func (export "run") (param i32 i32) (result i64) {run_body}))''')


def run(artifact: str, limits: ResourceLimits | None = None, payload: dict | None = None):
    return RuntimeHost.execute(RuntimeKind.WASM, artifact, PluginManifest(), payload or {"message": "hello"}, limits or ResourceLimits())


def test_real_wasm_roundtrips_nested_json_and_reports_consumed_fuel():
    artifact = encode((Path(__file__).parents[1] / "fixtures" / "json_echo.wat").read_text())
    payload = {"region": "EU", "nested": {"items": [1, True, "Azərbaycan"]}}
    output, status, error, latency, provenance, fuel = run(artifact, payload=payload)
    assert status == ExecutionStatus.SUCCESS, error
    assert output == payload
    assert provenance == "wasmtime-edge-json-v1"
    assert 0 < fuel < ResourceLimits().fuel
    assert latency >= 0


def test_infinite_loop_exhausts_fuel_without_hanging():
    artifact = module("(loop $forever (br $forever)) i64.const 0")
    # A generous deadline so that only fuel can stop the loop, even on a slow cold start.
    output, status, error, _, _, fuel = run(artifact, ResourceLimits(fuel=1000, timeout_ms=10_000))
    assert status == ExecutionStatus.TIMEOUT
    assert "fuel" in error
    assert fuel == 1000
    assert output == {}


def test_execution_deadline_interrupts_even_with_large_fuel_budget():
    artifact = module("(loop $forever (br $forever)) i64.const 0")
    _, status, error, latency, _, _ = run(artifact, ResourceLimits(fuel=100_000_000, timeout_ms=1))
    assert status == ExecutionStatus.TIMEOUT
    assert "fuel" not in error  # stopped by the deadline, not by exhausting fuel
    assert latency < 5000


@pytest.mark.parametrize(("artifact", "limits", "expected", "detail"), [
    (module("i64.const 0", pages=17), ResourceLimits(max_memory_mb=1), ExecutionStatus.ERROR, "memory"),
    (module("i64.const 0", alloc_body="i32.const -1"), ResourceLimits(), ExecutionStatus.ERROR, "input pointer"),
    (module("i64.const 429492434632705"), ResourceLimits(), ExecutionStatus.ERROR, "output range"),
    (module("i64.const 100"), ResourceLimits(max_output_bytes=10), ExecutionStatus.OUTPUT_LIMIT, "max_output_bytes"),
    (module("i64.const 1"), ResourceLimits(), ExecutionStatus.ERROR, "property name"),
    (module("unreachable"), ResourceLimits(), ExecutionStatus.TRAP, "unreachable"),
])
def test_guest_failures_are_bounded_and_explicit(artifact, limits, expected, detail):
    output, status, error, _, _, _ = run(artifact, limits)
    assert status == expected
    assert detail in error.lower()
    assert output == {}


def test_wasm_memory_growth_cannot_exceed_the_store_limit():
    artifact = module("i32.const 16 memory.grow i32.const -1 i32.ne if unreachable end local.get 1 i64.extend_i32_u")
    output, status, error, _, _, _ = run(artifact, ResourceLimits(max_memory_mb=1))
    assert status == ExecutionStatus.SUCCESS, error
    assert output == {"message": "hello"}


def test_host_imports_are_denied_even_if_manifest_declares_them():
    artifact = encode('''(module
      (import "env" "read_file" (func))
      (func (export "run") (param i32 i32) (result i64) i64.const 0))''')
    _, findings = WasmValidator.validate(artifact, PluginManifest(allowed_imports=["env.read_file"]))
    assert "host_imports_unavailable" in {finding.code for finding in findings}
    _, status, error, _, _, _ = run(artifact)
    assert status == ExecutionStatus.ERROR
    assert "imports" in error


def test_start_function_is_also_subject_to_fuel_limit():
    artifact = encode('''(module
      (func $start (loop $forever (br $forever)))
      (start $start))''')
    _, status, error, _, _, fuel = run(artifact, ResourceLimits(fuel=1000, timeout_ms=1000))
    assert status == ExecutionStatus.TIMEOUT
    assert "fuel" in error
    assert fuel == 1000


@pytest.mark.parametrize("output", ['{"value":NaN}', '{"value":1e999}', '[]', '{"value":' + '[' * 1200 + '0' + ']' * 1200 + '}'])
def test_invalid_json_values_and_excessive_nesting_are_execution_errors(output):
    data = "".join(f"\\{byte:02x}" for byte in output.encode())
    artifact = encode(f'''(module
      (memory (export "memory") 1)
      (data (i32.const 0) "{data}")
      (func (export "alloc") (param i32) (result i32) i32.const 8192)
      (func (export "run") (param i32 i32) (result i64) i64.const {len(output.encode())}))''')
    _, status, error, _, _, _ = run(artifact)
    assert status == ExecutionStatus.ERROR
    assert error
