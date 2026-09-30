import ipaddress
import re
import socket
import ssl
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Dict, List, Sequence, Tuple
from urllib.parse import urlparse

from post_quantum_crypto_migration_scanner.algorithms.rules import RulesEngine
from post_quantum_crypto_migration_scanner.domain.models import (
    Confidence, CryptoFinding, FindingType, ScanError, TLSObservation,
)


SECRET_PATTERN = re.compile(r"(?i)(private[_ -]?key|secret|password)\s*[:=]\s*[^\s,;]+")


def redact_excerpt(value: str, limit: int = 180) -> str:
    redacted = SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value.strip())
    if "-----BEGIN" in redacted and "PRIVATE KEY" in redacted:
        return "[REDACTED PRIVATE KEY MATERIAL]"
    return redacted[:limit]


class RepoScanner:
    PATTERNS: Sequence[Tuple[str, str, re.Pattern[str]]] = (
        ("MD5", "weak_hash", re.compile(r"(?i)\b(?:hashlib\.)?md5\s*\(")),
        ("SHA-1", "weak_hash", re.compile(r"(?i)\b(?:hashlib\.)?sha1\s*\(|SHA-?1")),
        ("RSA", "asymmetric", re.compile(r"(?i)\bRSA(?:\.generate|[-_ ]?2048|Encryption|/ECB)?\b")),
        ("ECDH", "asymmetric", re.compile(r"(?i)\bECDH\b|ecdh\.compute_key")),
        ("ECDSA", "asymmetric", re.compile(r"(?i)\bECDSA\b")),
        ("Diffie-Hellman", "asymmetric", re.compile(r"(?i)\bDiffie[- ]Hellman\b|\bDHE_")),
        ("AES-128", "symmetric", re.compile(r"(?i)\bAES[-_ ]?128\b")),
        ("AES-CBC", "symmetric", re.compile(r"(?i)\bAES(?:/|[-_ ])CBC\b|MODE_CBC")),
        ("ML-KEM", "pqc", re.compile(r"(?i)\bML[-_ ]?KEM\b|\bkyber(?:\.encrypt)?\b")),
        ("ML-DSA", "pqc", re.compile(r"(?i)\bML[-_ ]?DSA\b|\bdilithium\b")),
        ("hardcoded-key", "secret", re.compile(r"(?i)-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|private_key\s*=")),
        ("TLSv1.0", "protocol", re.compile(r"(?i)\bTLSv?1(?:\.0)?(?!\.\d)\b|PROTOCOL_TLSv1\b")),
        ("TLSv1.1", "protocol", re.compile(r"(?i)\bTLSv?1\.1\b")),
    )

    @staticmethod
    def _finding_type(path: str) -> FindingType:
        name = PurePosixPath(path).name.lower()
        if name in {"requirements.txt", "package-lock.json", "package.json", "pom.xml", "go.mod", "cargo.lock"}:
            return FindingType.DEPENDENCY
        if PurePosixPath(path).suffix.lower() in {".yaml", ".yml", ".json", ".toml", ".ini", ".conf", ".pem"}:
            return FindingType.CONFIG
        return FindingType.CODE

    @classmethod
    def scan(
        cls,
        files: Dict[str, str],
        *,
        retention_years: int = 1,
        internet_exposed: bool = False,
    ) -> List[CryptoFinding]:
        if len(files) > 1_000:
            raise ValueError("A service may contain at most 1,000 submitted files")
        if sum(len(content.encode("utf-8")) for content in files.values()) > 1_000_000:
            raise ValueError("Submitted repository content exceeds the 1 MB local scan limit")
        findings: List[CryptoFinding] = []
        seen = set()
        for path in sorted(files):
            content = files[path]
            if len(content.encode("utf-8")) > 250_000:
                raise ValueError(f"File exceeds 250 KB limit: {path}")
            for line_number, line in enumerate(content.splitlines() or [content], 1):
                for algorithm, _category, pattern in cls.PATTERNS:
                    if not pattern.search(line):
                        continue
                    key = (path, line_number, algorithm)
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(RulesEngine.evaluate_algorithm(
                        algorithm, path, cls._finding_type(path), line=line_number,
                        evidence=redact_excerpt(line), confidence=Confidence.HIGH,
                        retention_years=retention_years, internet_exposed=internet_exposed,
                    ))
        return findings


class TLSScanner:
    @staticmethod
    def analyze(
        endpoints: Sequence[object], service_name: str = "unknown", *, retention_years: int = 1,
        internet_exposed: bool = False,
    ) -> Tuple[List[CryptoFinding], List[ScanError]]:
        findings: List[CryptoFinding] = []
        errors: List[ScanError] = []
        for raw in endpoints:
            if isinstance(raw, TLSObservation):
                observation = raw
            elif isinstance(raw, dict):
                try:
                    observation = TLSObservation.model_validate(raw)
                except Exception as exc:
                    errors.append(ScanError(service_name=service_name, source=str(raw.get("endpoint", "tls")),
                                            code="invalid_tls_observation", message=str(exc)))
                    continue
            else:
                errors.append(ScanError(
                    service_name=service_name, source=str(raw), code="unverified_tls_endpoint",
                    message="Endpoint names are not simulated. Supply captured TLS metadata or use the authorized live probe.",
                ))
                continue
            source = observation.endpoint
            algorithms = [observation.protocol]
            algorithms.extend(value for value in (
                observation.cipher, observation.certificate_key_algorithm, observation.key_exchange,
            ) if value)
            for algorithm in algorithms:
                findings.append(RulesEngine.evaluate_algorithm(
                    algorithm, source, FindingType.TLS, evidence=f"{observation.provenance}: {algorithm}",
                    retention_years=retention_years, internet_exposed=internet_exposed,
                ))
            days = observation.certificate_days_remaining
            if days is not None and days < 30:
                findings.append(RulesEngine.evaluate_algorithm(
                    "certificate-expiry", source, FindingType.TLS,
                    evidence=f"certificate expired {-days} day(s) ago" if days < 0 else f"certificate expires in {days} day(s)",
                    retention_years=retention_years, internet_exposed=internet_exposed,
                ))
        return findings, errors

    @classmethod
    def scan(cls, endpoints: Sequence[object]) -> List[CryptoFinding]:
        return cls.analyze(endpoints)[0]

    @staticmethod
    def validate_live_target(endpoint: str) -> Tuple[str, int]:
        parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Only an https endpoint with a hostname is allowed")
        port = parsed.port or 443
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
        for item in addresses:
            ip = ipaddress.ip_address(item[4][0])
            if not ip.is_global:
                raise ValueError("Private, loopback, link-local, multicast, and reserved targets are blocked")
        return parsed.hostname, port

    @classmethod
    def probe(cls, endpoint: str, *, authorized: bool, timeout_seconds: float = 3.0) -> TLSObservation:
        if not authorized:
            raise PermissionError("Live probing requires explicit authorization")
        hostname, port = cls.validate_live_target(endpoint)
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout_seconds) as raw:
            with context.wrap_socket(raw, server_hostname=hostname) as tls:
                cert = tls.getpeercert()
                days = None
                if cert.get("notAfter"):
                    expires = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                    days = (expires - datetime.now(timezone.utc)).days
                cipher = tls.cipher()[0] if tls.cipher() else None
                return TLSObservation(
                    endpoint=f"https://{hostname}:{port}", protocol=tls.version() or "unknown",
                    cipher=cipher, certificate_days_remaining=days, provenance="authorized_live_probe",
                )
