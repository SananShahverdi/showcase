from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query as ApiQuery, Request, UploadFile
from pydantic import BaseModel, Field

from compliance_aware_rag_knowledge_base.adapters.repositories import AuditRepository, ChunkRepository, DocumentRepository, GovernanceRepository
from compliance_aware_rag_knowledge_base.algorithms.ingestion import DocumentParseError, extract_text, parser_name
from compliance_aware_rag_knowledge_base.domain.models import (
    Answer, Document, DocumentStatus, DocumentUpdate, EvaluationRun, Feedback, GoldenQuestion,
    Identity, Query, RedactionRule, Role, Sensitivity,
)
from compliance_aware_rag_knowledge_base.services.rag_service import RAGService

router = APIRouter()
doc_repo, chunk_repo, audit_repo, governance_repo = DocumentRepository(), ChunkRepository(), AuditRepository(), GovernanceRepository()
rag_service = RAGService(doc_repo, chunk_repo, audit_repo, governance_repo)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def identity(
    x_user_id: str = Header(default="demo-employee"),
    x_user_role: Role = Header(default=Role.EMPLOYEE),
    x_user_teams: str = Header(default="general"),
    x_user_clearance: Sensitivity = Header(default=Sensitivity.INTERNAL),
) -> Identity:
    return Identity(user_id=x_user_id, role=x_user_role, teams=[item.strip() for item in x_user_teams.split(",") if item.strip()], clearance=x_user_clearance)


def admin(current: Identity = Depends(identity)) -> Identity:
    if current.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required in demo identity context")
    return current


def document_summary(document: Document) -> Dict[str, Any]:
    payload = document.model_dump(mode="json", exclude={"content"})
    payload["chunk_count"] = len(chunk_repo.get_for_document(document.id))
    return payload


class QueryRequest(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    reason: str = Field(default="", max_length=1000)


class RedactionPreview(BaseModel):
    text: str = Field(max_length=10_000)
    pattern: str = Field(min_length=1, max_length=500)
    replacement: str = "[REDACTED]"


@router.post("/ingest", status_code=201)
async def ingest(
    file: UploadFile = File(...), title: str = Form(...), allowed_roles: str = Form(...),
    allowed_teams: str = Form(""), owner: str = Form("system"), team: str = Form("general"),
    sensitivity: Sensitivity = Form(Sensitivity.INTERNAL), source: str = Form("upload"),
    tags: str = Form(""), retention_days: int = Form(365), current: Identity = Depends(admin),
):
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Document exceeds {MAX_UPLOAD_BYTES} bytes")
    filename = Path(file.filename or "document.txt").name
    try:
        content = extract_text(file_bytes, file.content_type or "", filename)
        roles = [Role(item.strip()) for item in allowed_roles.split(",") if item.strip()]
        if not roles:
            raise ValueError("At least one allowed role is required")
        document = Document(
            title=title, content=content, filename=filename, file_type=file.content_type or "application/octet-stream",
            checksum_sha256=sha256(file_bytes).hexdigest(), parser=parser_name(file.content_type or "", filename),
            owner=owner, team=team, sensitivity=sensitivity, source=source,
            tags=[item.strip() for item in tags.split(",") if item.strip()], retention_days=retention_days,
            allowed_roles=roles, allowed_teams=[item.strip() for item in allowed_teams.split(",") if item.strip()],
        )
        chunks = rag_service.ingest_document(document, actor_id=current.user_id)
    except (DocumentParseError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"document": document_summary(document), "chunks_created": len(chunks)}


@router.post("/query", response_model=Answer)
def query(request: QueryRequest, http_request: Request, current: Identity = Depends(identity)) -> Answer:
    return rag_service.process_query(
        Query(user_id=current.user_id, user_role=current.role, user_teams=current.teams, clearance=current.clearance, text=request.text, top_k=request.top_k),
        request_id=http_request.headers.get("X-Request-ID"),
    )


@router.post("/answers/{answer_id}/feedback", response_model=Feedback, status_code=201)
def feedback(answer_id: UUID, request: FeedbackRequest, current: Identity = Depends(identity)) -> Feedback:
    try:
        return rag_service.record_feedback(answer_id, current.user_id, request.rating, request.reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/admin/documents")
def list_documents(_: Identity = Depends(admin)):
    return [document_summary(document) for document in doc_repo.get_all()]


@router.patch("/admin/documents/{document_id}")
def update_document(document_id: UUID, update: DocumentUpdate, current: Identity = Depends(admin)):
    try:
        return document_summary(rag_service.update_document(document_id, update, current.user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/admin/documents/{document_id}")
def delete_document(document_id: UUID, current: Identity = Depends(admin)):
    try:
        return document_summary(rag_service.set_document_status(document_id, DocumentStatus.DELETED, current.user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/admin/documents/{document_id}/restore")
def restore_document(document_id: UUID, current: Identity = Depends(admin)):
    try:
        return document_summary(rag_service.set_document_status(document_id, DocumentStatus.ACTIVE, current.user_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/admin/retention/preview")
def retention_preview(_: Identity = Depends(admin)):
    return [document_summary(item) for item in rag_service.retention_preview()]


@router.post("/admin/retention/enforce")
def retention_enforce(current: Identity = Depends(admin)):
    expired = rag_service.enforce_retention(current.user_id)
    return {"count": len(expired), "documents": [document_summary(item) for item in expired]}


@router.get("/admin/redactions", response_model=List[RedactionRule])
def list_redactions(_: Identity = Depends(admin)):
    return governance_repo.list_redactions()


@router.post("/admin/redactions", response_model=RedactionRule, status_code=201)
def save_redaction(rule: RedactionRule, current: Identity = Depends(admin)):
    try:
        return rag_service.save_redaction(rule, current.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/redactions/preview")
def preview_redaction(request: RedactionPreview, _: Identity = Depends(admin)):
    try:
        return {"original": request.text, "redacted": rag_service.preview_redaction(request.text, request.pattern, request.replacement)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/audit")
def get_audit_logs(limit: int = ApiQuery(default=100, ge=1, le=500), _: Identity = Depends(admin)):
    return audit_repo.get_all()[:limit]


@router.post("/admin/evaluations", response_model=EvaluationRun, status_code=201)
def run_evaluation(questions: List[GoldenQuestion], current: Identity = Depends(admin)):
    try:
        return rag_service.run_evaluation(questions, current.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/evaluations", response_model=List[EvaluationRun])
def list_evaluations(_: Identity = Depends(admin)):
    return governance_repo.list_evaluations()


@router.post("/demo/seed")
def seed_demo(current: Identity = Depends(admin)):
    documents = [
        Document(title="Product launch brief", filename="launch.md", file_type="text/markdown", content="Project Atlas launches in Q3 2026. The launch owner is Maya Chen. The approved launch budget is 2.4 million dollars.", owner="product", team="product", sensitivity=Sensitivity.INTERNAL, allowed_roles=[Role.EMPLOYEE, Role.ADMIN], allowed_teams=["product", "general"], tags=["launch"]),
        Document(title="Restricted security runbook", filename="security.txt", content="The emergency credential rotation window is Sunday at 02:00 UTC. Contact the security on-call before execution.", owner="security", team="security", sensitivity=Sensitivity.RESTRICTED, allowed_roles=[Role.ADMIN], allowed_teams=["security"], tags=["security"]),
        Document(title="Contractor onboarding", filename="onboarding.txt", content="Contractors receive repository access after sponsor approval and security training completion.", owner="people-ops", team="general", sensitivity=Sensitivity.INTERNAL, allowed_roles=[Role.CONTRACTOR, Role.EMPLOYEE, Role.ADMIN], tags=["onboarding"]),
    ]
    created = []
    existing_titles = {item.title for item in doc_repo.get_all() if item.status == DocumentStatus.ACTIVE}
    for document in documents:
        if document.title not in existing_titles:
            rag_service.ingest_document(document, actor_id=current.user_id)
            created.append(document_summary(document))
    return {"created_count": len(created), "documents": created}
