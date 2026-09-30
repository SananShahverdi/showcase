"""Synthetic demo estate used by the console's "Load & scan demo estate" action.

Every file, endpoint, and TLS value below is invented for demonstration. The
TLS entries are labelled ``seeded_capture`` so reports show that they were
supplied, not observed on a network.
"""

from typing import List

from post_quantum_crypto_migration_scanner.domain.models import ServiceScanInput


def demo_estate() -> List[ServiceScanInput]:
    return [
        ServiceScanInput(
            name="payment-api",
            retention_years=7,
            internet_exposed=True,
            files={
                "src/signing.py": "from Crypto.PublicKey import RSA\nkey = RSA.generate(2048)\ndigest = hashlib.sha1(payload)",
                "config/tls.yml": "minimum: TLSv1.0\nprivate_key=demo-secret",
            },
            endpoints=[{
                "endpoint": "https://payments.example.test", "protocol": "TLSv1.0",
                "certificate_key_algorithm": "RSA-2048", "provenance": "seeded_capture",
            }],
        ),
        ServiceScanInput(
            name="identity-hybrid",
            retention_years=2,
            internet_exposed=False,
            files={"src/kem.py": "ciphertext = kyber.encrypt(public_key)"},
            endpoints=[{
                "endpoint": "https://identity.example.test", "protocol": "TLSv1.3",
                "key_exchange": "ML-KEM-768", "provenance": "seeded_capture",
            }],
        ),
    ]
