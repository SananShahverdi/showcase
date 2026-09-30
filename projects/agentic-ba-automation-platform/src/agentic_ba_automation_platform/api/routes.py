from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from agentic_ba_automation_platform.adapters.repositories import InMemoryRepository
from agentic_ba_automation_platform.algorithms.document_worker import extract_text
from agentic_ba_automation_platform.domain.models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    AuditLog,
    Document,
    ExportResult,
)
from agentic_ba_automation_platform.services.automation_service import AutomationService

router = APIRouter()
repo = InMemoryRepository()
service = AutomationService(repo)

SUPPORTED_TYPES = {
    "text/plain",
    "text/markdown",
    "text/html",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
# Browsers often send no type (or a generic one) for Markdown and some other files;
# fall back to the extension the console's file picker already restricts to.
EXTENSION_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
TYPE_ALIASES = {"text/x-markdown": "text/markdown"}


def resolve_content_type(declared: str | None, filename: str | None) -> str:
    content_type = (declared or "").split(";")[0].strip().lower()
    content_type = TYPE_ALIASES.get(content_type, content_type)
    if content_type in {"", "application/octet-stream"}:
        extension = "." + (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
        return EXTENSION_TYPES.get(extension, content_type)
    return content_type


class GenerateRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    artifact_type: ArtifactType
    user_id: str = Field(min_length=1, max_length=100)


class StatusUpdateRequest(BaseModel):
    status: ArtifactStatus
    user_id: str = Field(min_length=1, max_length=100)
    comment: Optional[str] = Field(default=None, max_length=1000)


class EditArtifactRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    user_id: str = Field(min_length=1, max_length=100)


class ExportRequest(BaseModel):
    target: str = Field(pattern="^(json|jira|github)$")
    user_id: str = Field(min_length=1, max_length=100)


@router.post("/upload", response_model=Document)
async def upload_document(user_id: str = Form(...), file: UploadFile = File(...)):
    content_type = resolve_content_type(file.content_type, file.filename)
    if content_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported document type: {content_type or 'unknown'}")
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 5 MiB local limit")
    try:
        content = extract_text(file_bytes, content_type)
        return service.process_document(file.filename or "upload", content, content_type, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/documents", response_model=List[Document])
def list_documents():
    return repo.get_documents()


@router.post("/generate", response_model=Artifact)
def generate_artifact(request: GenerateRequest):
    try:
        return service.generate_artifact(request.query, request.artifact_type, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/artifacts", response_model=List[Artifact])
def list_artifacts(status: Optional[ArtifactStatus] = None):
    artifacts = repo.get_artifacts()
    return [item for item in artifacts if status is None or item.status == status]


@router.patch("/artifacts/{artifact_id}", response_model=Artifact)
def edit_artifact(artifact_id: UUID, request: EditArtifactRequest):
    try:
        artifact = service.edit_artifact(artifact_id, request.content, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.put("/artifacts/{artifact_id}/status", response_model=Artifact)
def update_status(artifact_id: UUID, request: StatusUpdateRequest):
    try:
        artifact = service.update_artifact_status(artifact_id, request.status, request.user_id, request.comment)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.post("/artifacts/{artifact_id}/export", response_model=ExportResult)
def export_artifact(artifact_id: UUID, request: ExportRequest):
    try:
        return service.export_artifact(artifact_id, request.target, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/audit", response_model=List[AuditLog])
def get_audit_logs(action: Optional[str] = None):
    logs = repo.get_audit_logs()
    return [log for log in logs if action is None or log.action == action]


@router.post("/demo/seed")
def seed_demo():
    return service.seed_demo()
