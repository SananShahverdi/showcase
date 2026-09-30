from typing import Dict, List

from fastapi import APIRouter, Header, HTTPException, Response

from internal_developer_portal_golden_paths.adapters.artifacts import LocalArtifactStore
from internal_developer_portal_golden_paths.adapters.repositories import CatalogStore
from internal_developer_portal_golden_paths.domain.models import (
    ArtifactManifest,
    DependencyGraph,
    ScaffoldRequest,
    ScaffoldResponse,
    ServiceMetadata,
    TemplateApprovalRequest,
    TemplateDefinition,
    TemplateStatus,
)
from internal_developer_portal_golden_paths.services.scaffolder import ScaffolderService

router = APIRouter()
catalog = CatalogStore()
artifacts = LocalArtifactStore()
scaffolder = ScaffolderService(catalog, artifacts)


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=409 if "already" in str(error).lower() else 400, detail=str(error))


def _require_admin(role: str) -> None:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Platform administrator role required")


@router.get("/templates", response_model=List[TemplateDefinition])
async def get_templates():
    return catalog.get_templates()


@router.post("/templates", response_model=TemplateDefinition, status_code=201)
async def create_template(template: TemplateDefinition, x_role: str = Header(default="developer")):
    _require_admin(x_role)
    draft = template.model_copy(update={"status": TemplateStatus.DRAFT, "approved_by": None, "approval_reason": None})
    try:
        catalog.add_template(draft)
    except ValueError as error:
        raise _bad_request(error) from error
    return draft


@router.post("/templates/{template_id}/approve", response_model=TemplateDefinition)
async def approve_template(template_id: str, request: TemplateApprovalRequest, x_role: str = Header(default="developer"), x_actor: str = Header(default="local-admin")):
    _require_admin(x_role)
    template = catalog.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    if len(request.reason.strip()) < 3:
        raise HTTPException(status_code=422, detail="Approval reason is required")
    approved = template.model_copy(update={
        "status": TemplateStatus.APPROVED,
        "approved_by": x_actor,
        "approval_reason": request.reason.strip(),
    })
    catalog.save_template(approved)
    return approved


@router.post("/scaffold/preview", response_model=Dict[str, List[str]])
async def preview_scaffold(request: ScaffoldRequest):
    try:
        return {"files": scaffolder.preview(request)}
    except ValueError as error:
        raise _bad_request(error) from error


@router.post("/scaffold", response_model=ScaffoldResponse)
async def scaffold_service(request: ScaffoldRequest, x_role: str = Header(default="developer")):
    if x_role not in {"developer", "owner", "admin"}:
        raise HTTPException(status_code=403, detail="Developer role required")
    try:
        return scaffolder.scaffold(request)
    except ValueError as error:
        raise _bad_request(error) from error


@router.get("/artifacts/{service_id}/manifest", response_model=ArtifactManifest)
async def artifact_manifest(service_id: str):
    manifest = artifacts.get_manifest(service_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Artifact manifest not found")
    return manifest


@router.get("/download/{service_id}")
async def download_artifact(service_id: str):
    content = artifacts.get_archive(service_id)
    service = catalog.get_service(service_id)
    if content is None or service is None:
        raise HTTPException(status_code=404, detail="Generated artifact not found")
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{service.name}.zip"',
            "X-Content-SHA256": artifacts.get_manifest(service_id).checksum_sha256,
        },
    )


@router.get("/catalog", response_model=List[ServiceMetadata])
async def get_catalog():
    return catalog.get_services()


@router.get("/catalog/graph/dependencies", response_model=DependencyGraph)
async def get_dependency_graph():
    return scaffolder.graph()


@router.get("/catalog/{service_id}", response_model=ServiceMetadata)
async def get_catalog_service(service_id: str):
    service = catalog.get_service(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Catalog service not found")
    return service
