from hashlib import sha256
from io import BytesIO
from typing import Dict
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from internal_developer_portal_golden_paths.domain.models import ArtifactManifest


class LocalArtifactStore:
    """Bounded, deterministic ZIP storage for local execution and tests."""

    MAX_FILES = 100
    MAX_UNCOMPRESSED_BYTES = 2_000_000

    def __init__(self):
        self.archives: Dict[str, bytes] = {}
        self.manifests: Dict[str, ArtifactManifest] = {}

    def put(self, service_id: str, template_id: str, template_version: str, files: Dict[str, str]) -> ArtifactManifest:
        if not files or len(files) > self.MAX_FILES:
            raise ValueError("Generated artifact has an invalid file count")
        if sum(len(content.encode()) for content in files.values()) > self.MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Generated artifact exceeds the local size limit")

        file_hashes: Dict[str, str] = {}
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for path in sorted(files):
                if path.startswith("/") or ".." in path.split("/") or "\\" in path:
                    raise ValueError(f"Unsafe generated path: {path}")
                payload = files[path].encode()
                file_hashes[path] = sha256(payload).hexdigest()
                info = ZipInfo(path, date_time=(2024, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, payload)
        content = buffer.getvalue()
        checksum = sha256(content).hexdigest()
        manifest = ArtifactManifest(
            service_id=service_id,
            template_id=template_id,
            template_version=template_version,
            checksum_sha256=checksum,
            files=file_hashes,
        )
        self.archives[service_id] = content
        self.manifests[service_id] = manifest
        return manifest

    def get_archive(self, service_id: str) -> bytes | None:
        return self.archives.get(service_id)

    def get_manifest(self, service_id: str) -> ArtifactManifest | None:
        return self.manifests.get(service_id)
