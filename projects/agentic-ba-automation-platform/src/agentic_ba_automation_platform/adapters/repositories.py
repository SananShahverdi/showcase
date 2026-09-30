from typing import List, Dict, Optional
from uuid import UUID
from agentic_ba_automation_platform.domain.models import Document, Chunk, Artifact, AuditLog

class InMemoryRepository:
    def __init__(self):
        self.documents: Dict[UUID, Document] = {}
        self.chunks: Dict[UUID, Chunk] = {}
        self.artifacts: Dict[UUID, Artifact] = {}
        self.audit_logs: Dict[UUID, AuditLog] = {}

    def save_document(self, doc: Document):
        self.documents[doc.id] = doc

    def save_chunks(self, chunks: List[Chunk]):
        for chunk in chunks:
            self.chunks[chunk.id] = chunk

    def get_all_chunks(self) -> List[Chunk]:
        return list(self.chunks.values())

    def get_documents(self) -> List[Document]:
        return sorted(self.documents.values(), key=lambda item: item.uploaded_at, reverse=True)

    def save_artifact(self, artifact: Artifact):
        self.artifacts[artifact.id] = artifact
        
    def get_artifact(self, artifact_id: UUID) -> Optional[Artifact]:
        return self.artifacts.get(artifact_id)

    def get_artifacts(self) -> List[Artifact]:
        return sorted(self.artifacts.values(), key=lambda item: item.updated_at, reverse=True)

    def save_audit_log(self, log: AuditLog):
        self.audit_logs[log.id] = log
        
    def get_audit_logs(self) -> List[AuditLog]:
        return sorted(self.audit_logs.values(), key=lambda item: item.timestamp, reverse=True)

    def reset(self):
        self.documents.clear()
        self.chunks.clear()
        self.artifacts.clear()
        self.audit_logs.clear()
