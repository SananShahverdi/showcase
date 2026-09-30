from fastapi.testclient import TestClient
import base64
from pathlib import Path
import wasmtime

from edge_wasm_plugin_runtime.api.app import app
from edge_wasm_plugin_runtime.algorithms.runtime_host import RuntimeHost

client = TestClient(app)


def local_version(tag: str, adapter: str):
    return {
        "version_tag": tag,
        "manifest": {
            "runtime_kind": "local_adapter",
            "local_adapter": adapter,
            "abi_version": "edge-json-v1",
            "entrypoint": "run",
            "allowed_imports": [],
        },
    }


def test_plugin_lifecycle_canary_activation_metrics_and_rollback():
    assert client.get("/health").status_code == 200
    registered = client.post("/api/plugins/route-plugin?name=Router&description=RoutesTraffic")
    assert registered.status_code == 200

    v1 = client.post("/api/plugins/route-plugin/versions", json=local_version("v1.0", "routing-policy"))
    assert v1.status_code == 200
    assert v1.json()["status"] == "validated"
    assert v1.json()["artifact"].startswith("adapter://")

    before_canary = client.post("/api/plugins/route-plugin/activate/v1.0", json={"actor": "operator"})
    assert before_canary.status_code == 409
    canary_v1 = client.post(
        "/api/plugins/route-plugin/versions/v1.0/canary", json={"payload": {"region": "EU"}}
    )
    assert canary_v1.status_code == 200
    assert canary_v1.json()["runtime_kind"] == "local_adapter"
    assert canary_v1.json()["output_payload"]["route"] == "eu-west-1"
    assert client.post("/api/plugins/route-plugin/activate/v1.0", json={"actor": "operator"}).status_code == 200

    execution = client.post("/api/execute", json={"plugin_id": "route-plugin", "payload": {"region": "US"}})
    assert execution.status_code == 200
    assert execution.json()["output_payload"]["route"] == "us-east-1"
    assert len(execution.json()["input_sha256"]) == 64

    v2 = client.post("/api/plugins/route-plugin/versions", json=local_version("v2.0", "alert-filter"))
    assert v2.status_code == 200
    assert client.post(
        "/api/plugins/route-plugin/versions/v2.0/canary", json={"payload": {"severity": "high"}}
    ).status_code == 200
    activated = client.post(
        "/api/plugins/route-plugin/activate/v2.0",
        json={"actor": "operator", "expected_active_version": "v1.0"},
    )
    assert activated.status_code == 200

    rolled_back = client.post("/api/plugins/route-plugin/rollback?actor=on-call")
    assert rolled_back.status_code == 200
    plugin = rolled_back.json()
    active = next(version for version in plugin["versions"] if version["id"] == plugin["active_version_id"])
    assert active["version_tag"] == "v1.0"
    assert plugin["activation_history"][-1]["action"] == "rollback"
    # Retried rollback is idempotent.
    assert client.post("/api/plugins/route-plugin/rollback?actor=on-call").status_code == 200

    history = client.get("/api/plugins/route-plugin/executions")
    assert history.status_code == 200
    assert len(history.json()) >= 3
    metrics = client.get("/api/plugins/route-plugin/versions/v1.0/metrics").json()
    assert metrics["executions"] >= 2
    benchmark = client.post(
        "/api/plugins/route-plugin/versions/v1.0/benchmark",
        json={"payload": {"region": "EU"}, "iterations": 3},
    )
    assert benchmark.status_code == 200
    assert benchmark.json()["label"] == "trusted local adapter benchmark"


def test_invalid_wasm_is_quarantined_and_not_simulated():
    assert client.post("/api/plugins/wasm-test?name=Wasm&description=Validation").status_code == 200
    # A real Wasm header but no required `run` export.
    uploaded = client.post("/api/plugins/wasm-test/versions", json={
        "version_tag": "0.1.0",
        "wasm_base64": "AGFzbQEAAAA=",
        "manifest": {"runtime_kind": "wasm", "entrypoint": "run"},
    })
    assert uploaded.status_code == 200
    assert uploaded.json()["status"] == "quarantined"
    assert uploaded.json()["validation_findings"][0]["code"] == "missing_entrypoint"
    assert client.post(
        "/api/plugins/wasm-test/versions/0.1.0/canary", json={"payload": {"action": "route"}}
    ).status_code == 409


def test_seeded_demo_exposes_three_honestly_labeled_adapters():
    seeded = client.post("/api/demo/seed")
    assert seeded.status_code == 200
    ids = {plugin["id"] for plugin in seeded.json()}
    assert {"data-cleaner", "alert-filter", "routing-policy"}.issubset(ids)
    capabilities = client.get("/api/runtime/capabilities").json()
    assert capabilities["wasm_execution_ready"] == RuntimeHost.runtime_available()
    assert capabilities["trusted_local_adapters"] == ["alert-filter", "data-cleaner", "routing-policy"]


def test_real_wasm_upload_canary_activation_and_execution():
    wat = (Path(__file__).parents[1] / "fixtures" / "json_echo.wat").read_text()
    artifact = base64.b64encode(wasmtime.wat2wasm(wat)).decode()
    assert client.post("/api/plugins/real-json?name=JSON&description=RealWasm").status_code == 200
    uploaded = client.post("/api/plugins/real-json/versions", json={
        "version_tag": "1.0.0", "wasm_base64": artifact,
        "manifest": {"runtime_kind": "wasm", "abi_version": "edge-json-v1"},
    })
    assert uploaded.status_code == 200
    assert uploaded.json()["status"] == "validated"
    canary = client.post("/api/plugins/real-json/versions/1.0.0/canary", json={"payload": {"canary": True}})
    assert canary.status_code == 200
    assert canary.json()["status"] == "success", canary.json()
    assert canary.json()["fuel_consumed"] > 0
    assert client.post("/api/plugins/real-json/activate/1.0.0", json={"actor": "tester"}).status_code == 200
    executed = client.post("/api/execute", json={"plugin_id": "real-json", "payload": {"message": "Live Wasm"}})
    assert executed.status_code == 200
    assert executed.json()["output_payload"] == {"message": "Live Wasm"}
    assert executed.json()["runtime_provenance"] == "wasmtime-edge-json-v1"
    assert client.get("/api/plugins/real-json/versions/1.0.0/metrics").json()["errors"] == 0


def test_seeded_real_wasm_transforms_payload_in_the_workbench():
    assert client.post("/api/demo/seed").status_code == 200
    response = client.post("/api/execute", json={
        "plugin_id": "json-normalizer", "payload": {"MESSAGE": "HELLO", "items": ["WORLD", 42]},
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success", response.json()
    assert response.json()["output_payload"] == {"message": "hello", "items": ["world", 42]}
    assert response.json()["runtime_kind"] == "wasm"
    assert client.get("/api/runtime/examples").json()[0]["wasm_base64"]
