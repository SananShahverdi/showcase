import re
from uuid import uuid4

from internal_developer_portal_golden_paths.adapters.artifacts import LocalArtifactStore
from internal_developer_portal_golden_paths.adapters.repositories import CatalogStore
from internal_developer_portal_golden_paths.algorithms.template_engine import TemplateEngine
from internal_developer_portal_golden_paths.domain.models import DependencyGraph, ScaffoldRequest, ScaffoldResponse, ServiceMetadata


SERVICE_NAME = re.compile(r"^[a-z][a-z0-9-]{1,61}[a-z0-9]$")


class ScaffolderService:
    def __init__(self, catalog: CatalogStore, artifacts: LocalArtifactStore):
        self.catalog = catalog
        self.artifacts = artifacts

    def _validate(self, req: ScaffoldRequest) -> None:
        if not SERVICE_NAME.fullmatch(req.service_name):
            raise ValueError("Service name must be a 3-63 character lowercase DNS label")
        if not req.owner.strip():
            raise ValueError("Owner is required")
        port = req.parameters.get("port")
        if port is not None and (not port.isdigit() or not 1024 <= int(port) <= 65535):
            raise ValueError("Port must be between 1024 and 65535")
        for dependency in req.dependencies:
            if self.catalog.get_service(dependency) is None:
                raise ValueError(f"Dependency {dependency} is not registered")

    def preview(self, req: ScaffoldRequest) -> list[str]:
        self._validate(req)
        template = self.catalog.get_template(req.template_id)
        if template is None:
            raise ValueError(f"Template {req.template_id} not found")
        if template.status != "approved":
            raise ValueError("Template is not approved for use")
        params = {**req.parameters, "service_name": req.service_name, "owner": req.owner}
        return sorted(TemplateEngine.render(req.template_id, params))

    def scaffold(self, req: ScaffoldRequest) -> ScaffoldResponse:
        self._validate(req)
        template = self.catalog.get_template(req.template_id)
        if template is None:
            raise ValueError(f"Template {req.template_id} not found")
        if template.status != "approved":
            raise ValueError("Template is not approved for use")

        params = {**req.parameters, "service_name": req.service_name, "owner": req.owner}
        files = TemplateEngine.render(req.template_id, params)
        service_id = str(uuid4())
        manifest = self.artifacts.put(service_id, template.id, template.version, files)
        metadata = ServiceMetadata(
            id=service_id,
            name=req.service_name,
            description=req.description,
            owner=req.owner,
            template_id=template.id,
            template_version=template.version,
            dependencies=req.dependencies,
            runbook_url=req.runbook_url,
        )
        try:
            self.catalog.add_service(metadata)
        except Exception:
            self.artifacts.archives.pop(service_id, None)
            self.artifacts.manifests.pop(service_id, None)
            raise
        return ScaffoldResponse(
            service_id=service_id,
            download_url=f"/api/download/{service_id}",
            files_generated=len(files),
            manifest_url=f"/api/artifacts/{service_id}/manifest",
            checksum_sha256=manifest.checksum_sha256,
        )

    def graph(self) -> DependencyGraph:
        services = self.catalog.get_services()
        edges = [
            {"source": service.id, "target": dependency}
            for service in services
            for dependency in service.dependencies
        ]
        return DependencyGraph(nodes=services, edges=edges)
