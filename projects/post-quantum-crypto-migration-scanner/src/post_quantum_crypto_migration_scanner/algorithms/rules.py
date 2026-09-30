import re
from typing import Optional

from post_quantum_crypto_migration_scanner.domain.models import (
    Confidence, CryptoFinding, FindingType, Severity,
)


# Post-quantum names that contain a classical token ("ML-DSA" contains "DSA").
# They are removed before the classical-exposure check so a PQC signature is not
# reported as Shor-vulnerable; a hybrid string that also names a classical
# primitive (for example "ECDSA+ML-DSA") is still flagged for its classical half.
PQC_TOKENS = ("ML-KEM", "MLKEM", "KYBER", "ML-DSA", "MLDSA", "DILITHIUM", "SLH-DSA", "SPHINCS")
PQC_NAMES = re.compile(r"(?:ML|SLH)-?DSA|ML-?KEM")
LEGACY_PROTOCOLS = {"TLSV1", "TLS1", "TLSV1.0", "TLSV1.1", "SSLV2", "SSLV3"}


class RulesEngine:
    RULE_VERSION = "2026.1"

    @classmethod
    def evaluate_algorithm(
        cls,
        algo: str,
        source: str,
        finding_type: FindingType,
        *,
        line: Optional[int] = None,
        evidence: Optional[str] = None,
        confidence: Confidence = Confidence.HIGH,
        retention_years: int = 1,
        internet_exposed: bool = False,
    ) -> CryptoFinding:
        normalized = algo.upper().replace("_", "-")
        severity = Severity.LOW
        remediation = "Verify the algorithm, key lifecycle, and crypto-agility abstraction."
        rule_id = "CRYPTO-INVENTORY"
        quantum_vulnerable = False

        classical_view = PQC_NAMES.sub("", normalized)

        if normalized == "CERTIFICATE-EXPIRY":
            severity, rule_id = Severity.MEDIUM, "TLS-CERTIFICATE-EXPIRY"
            remediation = "Renew the certificate before expiry and confirm the replacement key algorithm fits the migration plan."
        elif any(token in normalized for token in ("MD5", "SHA-1", "SHA1")):
            severity, rule_id = Severity.CRITICAL, "CRYPTO-WEAK-HASH"
            remediation = "Replace collision-sensitive use with SHA-256/SHA-3 and rotate affected signatures or integrity records."
        elif "HARDCODED-KEY" in normalized:
            severity, rule_id = Severity.CRITICAL, "CRYPTO-HARDCODED-KEY"
            remediation = "Remove embedded key material, revoke it, and load a rotated key from an approved secret manager."
        elif normalized in LEGACY_PROTOCOLS or any(token in normalized for token in ("TLSV1.0", "TLSV1.1", "TLS 1.0", "TLS 1.1")):
            # Python's ssl module reports TLS 1.0 as "TLSv1", so the bare form is legacy too.
            severity, rule_id = Severity.CRITICAL, "TLS-LEGACY-PROTOCOL"
            remediation = "Disable SSL and TLS 1.0/1.1 and require TLS 1.2 or 1.3 with an approved cipher policy."
        elif any(token in classical_view for token in ("RSA", "ECDH", "ECDSA", "ECC", "DSA", "DIFFIE-HELLMAN")):
            severity, rule_id, quantum_vulnerable = Severity.HIGH, "PQC-SHOR-EXPOSURE", True
            remediation = "Inventory protocol dependencies and pilot a standardized hybrid ML-KEM or ML-DSA migration through a crypto-agility interface."
        elif any(token in normalized for token in PQC_TOKENS):
            severity, rule_id = Severity.INFO, "PQC-STANDARD-CANDIDATE"
            remediation = "Verify the standardized parameter set, library provenance, hybrid interoperability, and operational key lifecycle."
        elif "AES-128" in normalized or "AES-CBC" in normalized:
            severity, rule_id = Severity.MEDIUM, "CRYPTO-SYMMETRIC-REVIEW"
            remediation = "Prefer an approved authenticated-encryption mode and assess the key size against long-term data sensitivity."
        elif normalized.startswith("TLSV1.2") or normalized.startswith("TLSV1.3"):
            severity, rule_id = Severity.INFO, "TLS-PROTOCOL-INVENTORY"
            remediation = "Retain the observation and separately assess the negotiated key exchange for quantum exposure."

        base = {Severity.INFO: 5, Severity.LOW: 20, Severity.MEDIUM: 45, Severity.HIGH: 70, Severity.CRITICAL: 90}[severity]
        if quantum_vulnerable and retention_years >= 5:
            base += 10
        if internet_exposed and severity in (Severity.HIGH, Severity.CRITICAL):
            base += 10
        priority = min(base, 100)
        return CryptoFinding(
            type=finding_type,
            source=source,
            algorithm=algo,
            severity=severity,
            description=f"Detected {algo} with {confidence.value} confidence.",
            remediation=remediation,
            rule_id=rule_id,
            rule_version=cls.RULE_VERSION,
            line=line,
            evidence=evidence,
            confidence=confidence,
            quantum_vulnerable=quantum_vulnerable,
            migration_priority=priority,
        )
