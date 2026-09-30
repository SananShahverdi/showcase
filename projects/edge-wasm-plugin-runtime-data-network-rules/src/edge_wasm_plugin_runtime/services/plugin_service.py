import hashlib
import json
from typing import Dict, List, Optional

from edge_wasm_plugin_runtime.adapters.repositories import PluginRepository
from edge_wasm_plugin_runtime.algorithms.runtime_host import ALLOWED_ADAPTERS, RuntimeHost, WasmValidator
from edge_wasm_plugin_runtime.domain.models import (
    ActivationRecord, BenchmarkReport, ExecutionRequest, ExecutionResult, ExecutionStatus,
    Plugin, PluginManifest, PluginMetrics, PluginVersion, RuntimeKind, VersionStatus,
)


def percentile(values: List[float], quantile: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = (len(values) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


class PluginService:
    def __init__(self, repo: PluginRepository):
        self.repo = repo
        self.executions: List[ExecutionResult] = []

    def register_plugin(self, plugin_id: str, name: str, desc: str) -> Plugin:
        if self.repo.get_plugin(plugin_id):
            raise ValueError("Plugin already exists")
        plugin = Plugin(id=plugin_id, name=name, description=desc)
        self.repo.save_plugin(plugin)
        return plugin

    @staticmethod
    def _version(plugin: Plugin, version_tag: str) -> PluginVersion:
        version = next((item for item in plugin.versions if item.version_tag == version_tag), None)
        if version is None:
            raise ValueError("Version not found")
        return version

    def upload_version(
        self, plugin_id: str, version_tag: str, wasm_base64: Optional[str], manifest: PluginManifest,
    ) -> PluginVersion:
        plugin = self.repo.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        if any(version.version_tag == version_tag for version in plugin.versions):
            raise ValueError("Version tag already exists and versions are immutable")
        findings = []
        if manifest.runtime_kind == RuntimeKind.LOCAL_ADAPTER:
            if manifest.local_adapter not in ALLOWED_ADAPTERS:
                raise ValueError("local_adapter must name one of the trusted seeded adapters")
            if wasm_base64:
                raise ValueError("A local adapter version cannot include a Wasm artifact")
            artifact_bytes = f"adapter://{manifest.local_adapter}".encode("utf-8")
            artifact = artifact_bytes.decode("utf-8")
        else:
            if not wasm_base64:
                raise ValueError("wasm_base64 is required for a Wasm version")
            artifact_bytes, findings = WasmValidator.validate(wasm_base64, manifest)
            artifact = wasm_base64
        digest = hashlib.sha256(artifact_bytes).hexdigest()
        if any(version.artifact_sha256 == digest for version in plugin.versions):
            raise ValueError("This immutable artifact is already registered under another version")
        status = VersionStatus.QUARANTINED if any(item.blocking for item in findings) else VersionStatus.VALIDATED
        version = PluginVersion(
            plugin_id=plugin_id, version_tag=version_tag, artifact=artifact, artifact_sha256=digest,
            artifact_size_bytes=len(artifact_bytes), manifest=manifest, status=status,
            validation_findings=findings,
        )
        plugin.versions.append(version)
        self.repo.save_plugin(plugin)
        return version

    def canary(self, plugin_id: str, version_tag: str, payload: Dict) -> ExecutionResult:
        plugin = self.repo.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        version = self._version(plugin, version_tag)
        if version.status != VersionStatus.VALIDATED:
            raise ValueError("Only a validated version may run a canary")
        result = self._execute_version(plugin, version, payload)
        if result.status == ExecutionStatus.SUCCESS:
            version.canary_passed = True
            self.repo.save_plugin(plugin)
        return result

    def activate_version(
        self, plugin_id: str, version_tag: str, actor: str = "local-operator",
        expected_active_version: Optional[str] = None,
    ) -> Plugin:
        plugin = self.repo.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        version = self._version(plugin, version_tag)
        current = next((item for item in plugin.versions if item.id == plugin.active_version_id), None)
        current_tag = current.version_tag if current else None
        if expected_active_version is not None and expected_active_version != current_tag:
            raise RuntimeError(f"Activation conflict: expected {expected_active_version}, found {current_tag}")
        if version.status != VersionStatus.VALIDATED:
            raise ValueError("Quarantined versions cannot be activated")
        if not version.canary_passed:
            raise ValueError("A successful canary is required before activation")
        if plugin.active_version_id == version.id:
            return plugin
        record = ActivationRecord(
            plugin_id=plugin_id, from_version_id=plugin.active_version_id,
            to_version_id=version.id, action="activate", actor=actor,
        )
        plugin.active_version_id = version.id
        plugin.activation_history.append(record)
        self.repo.save_plugin(plugin)
        return plugin

    def rollback(self, plugin_id: str, actor: str = "local-operator") -> Plugin:
        plugin = self.repo.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        if plugin.activation_history and plugin.activation_history[-1].action == "rollback" \
                and plugin.activation_history[-1].to_version_id == plugin.active_version_id:
            return plugin
        previous = next((
            record.from_version_id for record in reversed(plugin.activation_history)
            if record.action == "activate" and record.to_version_id == plugin.active_version_id and record.from_version_id
        ), None)
        if previous is None:
            raise ValueError("No prior activated version is available for rollback")
        target = next((version for version in plugin.versions if version.id == previous), None)
        if target is None or target.status != VersionStatus.VALIDATED:
            raise ValueError("Prior version is not available and validated")
        record = ActivationRecord(
            plugin_id=plugin_id, from_version_id=plugin.active_version_id, to_version_id=target.id,
            action="rollback", actor=actor,
        )
        plugin.active_version_id = target.id
        plugin.activation_history.append(record)
        self.repo.save_plugin(plugin)
        return plugin

    def _execute_version(self, plugin: Plugin, version: PluginVersion, payload: Dict) -> ExecutionResult:
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        output, status, error, latency, provenance, fuel_consumed = RuntimeHost.execute(
            version.manifest.runtime_kind, version.artifact, version.manifest, payload, plugin.limits,
        )
        result = ExecutionResult(
            plugin_id=plugin.id, version_tag=version.version_tag, artifact_sha256=version.artifact_sha256,
            runtime_kind=version.manifest.runtime_kind, runtime_provenance=provenance,
            input_sha256=hashlib.sha256(encoded).hexdigest(), status=status,
            output_payload=output if status == ExecutionStatus.SUCCESS else None,
            error_message=error, latency_ms=round(latency, 4), fuel_consumed=fuel_consumed,
        )
        self.executions.append(result)
        return result

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        plugin = self.repo.get_plugin(request.plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        if plugin.active_version_id is None:
            raise ValueError("Plugin has no active version")
        version = next((item for item in plugin.versions if item.id == plugin.active_version_id), None)
        if version is None:
            raise ValueError("Active version data not found")
        return self._execute_version(plugin, version, request.payload)

    def history(self, plugin_id: str, limit: int = 100) -> List[ExecutionResult]:
        if self.repo.get_plugin(plugin_id) is None:
            raise ValueError("Plugin not found")
        matches = [item for item in self.executions if item.plugin_id == plugin_id]
        return list(reversed(matches[-limit:]))

    def metrics(self, plugin_id: str, version_tag: str) -> PluginMetrics:
        plugin = self.repo.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        self._version(plugin, version_tag)
        matches = [item for item in self.executions if item.plugin_id == plugin_id and item.version_tag == version_tag]
        latencies = [item.latency_ms for item in matches]
        errors = sum(item.status != ExecutionStatus.SUCCESS for item in matches)
        return PluginMetrics(
            plugin_id=plugin_id, version_tag=version_tag, executions=len(matches), errors=errors,
            error_rate=round(errors / len(matches), 4) if matches else 0.0,
            p50_latency_ms=round(percentile(latencies, .50), 4),
            p95_latency_ms=round(percentile(latencies, .95), 4),
            p99_latency_ms=round(percentile(latencies, .99), 4),
        )

    def benchmark(self, plugin_id: str, version_tag: str, payload: Dict, iterations: int) -> BenchmarkReport:
        plugin = self.repo.get_plugin(plugin_id)
        if plugin is None:
            raise ValueError("Plugin not found")
        version = self._version(plugin, version_tag)
        if version.status != VersionStatus.VALIDATED:
            raise ValueError("Only validated versions may be benchmarked")
        results = [self._execute_version(plugin, version, payload) for _ in range(iterations)]
        latencies = [result.latency_ms for result in results]
        return BenchmarkReport(
            plugin_id=plugin_id, version_tag=version_tag, runtime_kind=version.manifest.runtime_kind,
            label="trusted local adapter benchmark" if version.manifest.runtime_kind == RuntimeKind.LOCAL_ADAPTER else "wasm host benchmark",
            iterations=iterations, average_latency_ms=round(sum(latencies) / len(latencies), 4),
            p95_latency_ms=round(percentile(latencies, .95), 4),
        )
