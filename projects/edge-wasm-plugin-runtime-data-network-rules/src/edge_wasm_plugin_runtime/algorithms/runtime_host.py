import base64
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from edge_wasm_plugin_runtime.domain.models import (
    ExecutionStatus, PluginManifest, ResourceLimits, RuntimeKind, ValidationFinding,
)


ALLOWED_ADAPTERS = {"data-cleaner", "alert-filter", "routing-policy"}


def _read_u32(data: bytes, offset: int) -> Tuple[int, int]:
    result, shift = 0, 0
    for _ in range(5):
        if offset >= len(data):
            raise ValueError("truncated LEB128 value")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return result, offset
        shift += 7
    raise ValueError("invalid LEB128 value")


def _read_name(data: bytes, offset: int) -> Tuple[str, int]:
    length, offset = _read_u32(data, offset)
    end = offset + length
    if end > len(data):
        raise ValueError("truncated Wasm name")
    return data[offset:end].decode("utf-8"), end


class WasmValidator:
    MAX_ARTIFACT_BYTES = 2_000_000

    @classmethod
    def decode(cls, encoded: str) -> bytes:
        try:
            artifact = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError("wasm_base64 is not strict base64") from exc
        if len(artifact) > cls.MAX_ARTIFACT_BYTES:
            raise ValueError("Decoded Wasm exceeds the 2 MB artifact limit")
        return artifact

    @classmethod
    def inspect(cls, artifact: bytes) -> Tuple[List[str], List[str], List[ValidationFinding]]:
        findings: List[ValidationFinding] = []
        imports: List[str] = []
        exports: List[str] = []
        if len(artifact) < 8 or artifact[:4] != b"\x00asm" or artifact[4:8] != b"\x01\x00\x00\x00":
            return imports, exports, [ValidationFinding(code="invalid_wasm_header", message="Artifact is not a Wasm v1 binary")]
        offset = 8
        try:
            while offset < len(artifact):
                section_id = artifact[offset]
                offset += 1
                size, offset = _read_u32(artifact, offset)
                end = offset + size
                if end > len(artifact):
                    raise ValueError("section extends beyond artifact")
                section = artifact[offset:end]
                if section_id == 2:
                    count, cursor = _read_u32(section, 0)
                    for _ in range(count):
                        module, cursor = _read_name(section, cursor)
                        field, cursor = _read_name(section, cursor)
                        imports.append(f"{module}.{field}")
                        kind = section[cursor]
                        cursor += 1
                        if kind == 0:
                            _, cursor = _read_u32(section, cursor)
                        elif kind == 1:
                            cursor += 1
                            flags, cursor = _read_u32(section, cursor)
                            _, cursor = _read_u32(section, cursor)
                            if flags & 1:
                                _, cursor = _read_u32(section, cursor)
                        elif kind == 2:
                            flags, cursor = _read_u32(section, cursor)
                            _, cursor = _read_u32(section, cursor)
                            if flags & 1:
                                _, cursor = _read_u32(section, cursor)
                        elif kind == 3:
                            cursor += 2
                        else:
                            raise ValueError("unknown import kind")
                elif section_id == 7:
                    count, cursor = _read_u32(section, 0)
                    for _ in range(count):
                        name, cursor = _read_name(section, cursor)
                        exports.append(name)
                        cursor += 1
                        _, cursor = _read_u32(section, cursor)
                offset = end
        except (ValueError, UnicodeDecodeError, IndexError) as exc:
            findings.append(ValidationFinding(code="malformed_wasm", message=f"Cannot parse module sections: {exc}"))
        return imports, exports, findings

    @classmethod
    def validate(cls, encoded: str, manifest: PluginManifest) -> Tuple[bytes, List[ValidationFinding]]:
        artifact = cls.decode(encoded)
        imports, exports, findings = cls.inspect(artifact)
        undeclared = sorted(set(imports) - set(manifest.allowed_imports))
        if undeclared:
            findings.append(ValidationFinding(code="forbidden_import", message="Undeclared imports: " + ", ".join(undeclared)))
        if manifest.entrypoint not in exports:
            findings.append(ValidationFinding(code="missing_entrypoint", message=f"Required export '{manifest.entrypoint}' is missing"))
        if any(name.startswith("wasi_") or name.startswith("wasi:") for name in imports):
            findings.append(ValidationFinding(code="wasi_denied", message="WASI imports are denied by the default policy"))
        if imports and not undeclared:
            findings.append(ValidationFinding(code="host_imports_unavailable", message="This host provides no imports; use a self-contained module"))
        if manifest.abi_version != "edge-json-v1":
            findings.append(ValidationFinding(code="unsupported_abi", message="Only edge-json-v1 is supported"))
        if not findings and RuntimeHost.runtime_available():
            import wasmtime
            try:
                with wasmtime.Engine() as engine:
                    wasmtime.Module.validate(engine, artifact)
            except wasmtime.WasmtimeError as exc:
                findings.append(ValidationFinding(code="invalid_module", message=str(exc)[:500]))
        return artifact, findings


class RuntimeHost:
    @staticmethod
    def runtime_available() -> bool:
        try:
            import wasmtime  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _local_adapter(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if name == "data-cleaner":
            return {key: value.strip().lower() if isinstance(value, str) else value for key, value in payload.items()}
        if name == "alert-filter":
            severity = str(payload.get("severity", "unknown")).lower()
            return {**payload, "drop": severity in {"debug", "info", "low"}, "decision": "suppress" if severity in {"debug", "info", "low"} else "forward"}
        if name == "routing-policy":
            region = str(payload.get("region", "")).upper()
            return {**payload, "route": "eu-west-1" if region in {"EU", "EMEA"} else "us-east-1"}
        raise ValueError("Unknown trusted local adapter")

    @classmethod
    def execute(
        cls, runtime_kind: RuntimeKind, artifact: str, manifest: PluginManifest,
        payload: Dict[str, Any], limits: ResourceLimits,
    ) -> Tuple[Dict[str, Any], ExecutionStatus, str | None, float, str, Optional[int]]:
        start = time.perf_counter()
        encoded_input = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if len(encoded_input) > limits.max_input_bytes:
            return {}, ExecutionStatus.ERROR, "Input exceeds max_input_bytes", 0.0, "host-policy", None
        if runtime_kind == RuntimeKind.LOCAL_ADAPTER:
            try:
                output = cls._local_adapter(manifest.local_adapter or "", payload)
                encoded_output = json.dumps(output, separators=(",", ":"), sort_keys=True).encode("utf-8")
                if len(encoded_output) > limits.max_output_bytes:
                    return {}, ExecutionStatus.OUTPUT_LIMIT, "Output exceeds max_output_bytes", (time.perf_counter() - start) * 1000, "trusted-python-adapter-v1", None
                elapsed = (time.perf_counter() - start) * 1000
                if elapsed > limits.timeout_ms:
                    return {}, ExecutionStatus.TIMEOUT, "Execution exceeded timeout_ms", elapsed, "trusted-python-adapter-v1", None
                return output, ExecutionStatus.SUCCESS, None, elapsed, "trusted-python-adapter-v1", None
            except Exception as exc:
                return {}, ExecutionStatus.ERROR, str(exc)[:500], (time.perf_counter() - start) * 1000, "trusted-python-adapter-v1", None
        if not cls.runtime_available():
            return {}, ExecutionStatus.RUNTIME_UNAVAILABLE, "Install wasmtime to execute Wasm artifacts", (time.perf_counter() - start) * 1000, "wasmtime-unavailable", None
        from edge_wasm_plugin_runtime.algorithms.wasmtime_executor import execute_wasm
        try:
            decoded = WasmValidator.decode(artifact)
        except ValueError as exc:
            return {}, ExecutionStatus.ERROR, str(exc), 0.0, "host-policy", None
        return execute_wasm(decoded, manifest, encoded_input, limits)
