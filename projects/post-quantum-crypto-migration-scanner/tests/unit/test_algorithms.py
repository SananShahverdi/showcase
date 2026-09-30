from post_quantum_crypto_migration_scanner.domain.models import Severity, FindingType
from post_quantum_crypto_migration_scanner.algorithms.scanners import RepoScanner, TLSScanner
from post_quantum_crypto_migration_scanner.algorithms.rules import RulesEngine

def test_rules_engine():
    res1 = RulesEngine.evaluate_algorithm("MD5", "test.py", FindingType.CODE)
    assert res1.severity == Severity.CRITICAL
    
    res2 = RulesEngine.evaluate_algorithm("RSA-2048", "config.json", FindingType.CODE)
    assert res2.severity == Severity.HIGH
    assert res2.quantum_vulnerable is True
    
    res3 = RulesEngine.evaluate_algorithm("ML-KEM-768", "crypto.go", FindingType.CODE)
    assert res3.severity == Severity.INFO

def test_repo_scanner():
    files = {
        "legacy.py": "def foo(): return hashlib.md5(b'data')",
        "agile.py": "def foo(): return kyber.encrypt()"
    }
    findings = RepoScanner.scan(files)
    assert len(findings) == 2
    md5 = next(finding for finding in findings if finding.algorithm == "MD5")
    pqc = next(finding for finding in findings if finding.algorithm == "ML-KEM")
    assert md5.severity == Severity.CRITICAL
    assert md5.line == 1
    assert md5.rule_id == "CRYPTO-WEAK-HASH"
    assert pqc.severity == Severity.INFO

def test_tls_scanner():
    findings = TLSScanner.scan([
        {"endpoint": "legacy.example.test", "protocol": "TLSv1.0", "certificate_key_algorithm": "RSA-2048"},
        {"endpoint": "agile.example.test", "protocol": "TLSv1.3", "key_exchange": "ML-KEM-768"},
    ])
    assert len(findings) == 4


def test_secret_evidence_is_redacted_and_endpoint_names_are_not_simulated():
    findings = RepoScanner.scan({"settings.py": "private_key=super-secret RSA.generate(2048)"})
    assert findings
    assert all("super-secret" not in (finding.evidence or "") for finding in findings)

    findings, errors = TLSScanner.analyze(["https://legacy.example.test"], "payments")
    assert findings == []
    assert errors[0].code == "unverified_tls_endpoint"


def test_live_probe_blocks_local_targets():
    try:
        TLSScanner.validate_live_target("https://127.0.0.1:443")
    except ValueError as exc:
        assert "blocked" in str(exc)
    else:
        raise AssertionError("loopback endpoint must be rejected")


def test_post_quantum_signatures_are_not_reported_as_classical_exposure():
    for name in ("ML-DSA-65", "SLH-DSA-SHA2-128s", "X25519MLKEM768"):
        finding = RulesEngine.evaluate_algorithm(name, "tls", FindingType.TLS)
        assert finding.rule_id == "PQC-STANDARD-CANDIDATE", name
        assert finding.quantum_vulnerable is False
    # A hybrid that still names a classical primitive keeps its classical exposure.
    hybrid = RulesEngine.evaluate_algorithm("ECDSA-P256+ML-DSA-44", "tls", FindingType.TLS)
    assert hybrid.rule_id == "PQC-SHOR-EXPOSURE"
    assert RulesEngine.evaluate_algorithm("ECDSA", "tls", FindingType.TLS).quantum_vulnerable is True


def test_legacy_protocol_names_reported_by_live_probes_are_critical():
    # ssl.SSLSocket.version() reports TLS 1.0 as "TLSv1".
    for protocol in ("TLSv1", "TLSv1.1", "SSLv3"):
        finding = RulesEngine.evaluate_algorithm(protocol, "tls", FindingType.TLS)
        assert (finding.severity, finding.rule_id) == (Severity.CRITICAL, "TLS-LEGACY-PROTOCOL"), protocol
    assert RulesEngine.evaluate_algorithm("TLSv1.2", "tls", FindingType.TLS).rule_id == "TLS-PROTOCOL-INVENTORY"


def test_expiring_certificate_is_an_actionable_finding():
    findings = TLSScanner.scan([{"endpoint": "a.example.test", "protocol": "TLSv1.3", "certificate_days_remaining": -2}])
    expiry = next(finding for finding in findings if finding.algorithm == "certificate-expiry")
    assert expiry.rule_id == "TLS-CERTIFICATE-EXPIRY"
    assert expiry.severity == Severity.MEDIUM
    assert expiry.evidence == "certificate expired 2 day(s) ago"
