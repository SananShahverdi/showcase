from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    DEVELOPER = "developer"
    OWNER = "owner"
    ADMIN = "admin"
    AUDITOR = "auditor"

class Environment(BaseModel):
    name: str
    url: str

class ServiceMetadata(BaseModel):
    id: str
    name: str
    description: str
    owner: str
    template_id: str
    template_version: str
    lifecycle: str = "experimental"
    dependencies: List[str] = Field(default_factory=list)
    environments: List[Environment] = Field(default_factory=list)
    runbook_url: Optional[str] = None
    repo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TemplateStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"

class TemplateDefinition(BaseModel):
    id: str
    name: str
    version: str
    description: str
    status: TemplateStatus = TemplateStatus.DRAFT
    parameters: Dict[str, str] = Field(default_factory=dict)
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None

class ScaffoldRequest(BaseModel):
    template_id: str
    service_name: str
    owner: str
    description: str = "Generated through an approved golden path"
    dependencies: List[str] = Field(default_factory=list)
    runbook_url: Optional[str] = None
    parameters: Dict[str, str] = Field(default_factory=dict)

class ScaffoldResponse(BaseModel):
    service_id: str
    download_url: str
    files_generated: int
    manifest_url: str
    checksum_sha256: str

class ArtifactManifest(BaseModel):
    service_id: str
    template_id: str
    template_version: str
    checksum_sha256: str
    files: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TemplateApprovalRequest(BaseModel):
    actor: str = "local-admin"
    reason: str

class DependencyGraph(BaseModel):
    nodes: List[ServiceMetadata] = Field(default_factory=list)
    edges: List[Dict[str, str]] = Field(default_factory=list)
