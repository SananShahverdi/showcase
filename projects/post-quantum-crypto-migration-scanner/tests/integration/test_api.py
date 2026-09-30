from fastapi.testclient import TestClient
from post_quantum_crypto_migration_scanner.api.app import app

client = TestClient(app)

def test_full_scan_flow():
    # 1. Health
    assert client.get("/health").status_code == 200
    
    # 2. Submit a payload for scan
    payload = [
        {
            "name": "payment-service",
            "files": {
                "auth.py": "hashlib.md5()",
                "cert.pem": "RSA.generate()"
            },
            "endpoints": [
                {
                    "endpoint": "https://payments.example.test",
                    "protocol": "TLSv1.0",
                    "certificate_key_algorithm": "RSA-2048",
                    "provenance": "seeded_capture"
                }
            ],
            "retention_years": 7,
            "internet_exposed": True
        },
        {
            "name": "crypto-agile-service",
            "files": {
                "key_exchange.py": "kyber.encrypt()"
            },
            "endpoints": [
                {
                    "endpoint": "https://agile.example.test",
                    "protocol": "TLSv1.3",
                    "key_exchange": "ML-KEM-768",
                    "provenance": "seeded_capture"
                }
            ]
        }
    ]
    
    resp_scan = client.post("/api/scan", json=payload)
    assert resp_scan.status_code == 200
    report = resp_scan.json()
    
    # 3. Check report structure (Acceptance criteria 1, 2, 3)
    assert report["total_findings"] > 0
    assert report["critical_findings"] > 0
    assert len(report["services"]) == 2
    
    # payment-service is not quantum safe
    payment_svc = next(s for s in report["services"] if s["service_name"] == "payment-service")
    assert payment_svc["is_quantum_safe"] is False
    assert len(payment_svc["findings"]) == 4 # md5, rsa, tls1.0, rsa-2048 from endpoint
    
    # crypto-agile-service is quantum safe
    agile_svc = next(s for s in report["services"] if s["service_name"] == "crypto-agile-service")
    assert agile_svc["is_quantum_safe"] is True
    assert len(agile_svc["findings"]) == 3 # ml-kem from code, tls1.3, ml-kem from endpoint
    
    # 4. Dashboard (Acceptance criteria 4)
    resp_dash = client.get("/api/dashboard")
    assert resp_dash.status_code == 200
    dash_report = resp_dash.json()
    assert dash_report["id"] == report["id"]

    # 5. Evidence-backed migration plan and report export.
    assert report["migration_plan"][0]["service_name"] == "payment-service"
    assert report["migration_plan"][0]["priority"] == 100
    exported = client.get(f"/api/scans/{report['id']}/export")
    assert exported.status_code == 200
    assert "Migration order" in exported.text
    assert "PQC-SHOR-EXPOSURE" in exported.text


def test_unverified_endpoint_is_a_coverage_error_not_a_fake_result():
    response = client.post("/api/scan", json=[{
        "name": "unknown-tls",
        "files": {},
        "endpoints": ["https://legacy.example.test"]
    }])
    assert response.status_code == 200
    report = response.json()
    assert report["total_findings"] == 0
    assert report["errors"][0]["code"] == "unverified_tls_endpoint"
    assert report["services"][0]["posture"] == "unknown"

    forbidden = client.post("/api/tls/probe", json={
        "endpoint": "https://127.0.0.1", "authorized": False
    })
    assert forbidden.status_code == 403


def test_demo_seed_scans_the_synthetic_estate_and_is_listed():
    before = client.get("/api/scans")
    assert before.status_code == 200
    seeded = client.post("/api/demo/seed")
    assert seeded.status_code == 200
    report = seeded.json()
    assert [service["service_name"] for service in report["services"]] == ["payment-api", "identity-hybrid"]
    assert all(
        finding["evidence"].startswith("seeded_capture")
        for service in report["services"] for finding in service["findings"] if finding["type"] == "tls"
    )
    payment = report["services"][0]
    assert payment["posture"] == "action_required"
    assert "demo-secret" not in str(payment["findings"])
    assert report["services"][1]["is_quantum_safe"] is True

    listed = client.get("/api/scans").json()
    assert len(listed) == len(before.json()) + 1
    assert listed[0]["id"] == report["id"]
    assert listed[0]["service_count"] == 2
    assert listed[0]["critical_findings"] == report["critical_findings"]
    assert client.get("/api/dashboard").json()["id"] == report["id"]
