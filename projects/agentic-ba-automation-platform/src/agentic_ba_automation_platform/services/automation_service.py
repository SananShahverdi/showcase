import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from agentic_ba_automation_platform.adapters.repositories import InMemoryRepository
from agentic_ba_automation_platform.algorithms.agent_layer import generate_artifact as build_artifact
from agentic_ba_automation_platform.algorithms.rag import chunk_document, retrieve_chunks
from agentic_ba_automation_platform.domain.models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    AuditLog,
    Document,
    ExportResult,
)


class AutomationService:
    def __init__(self, repo: InMemoryRepository):
        self.repo = repo

    def process_document(self, filename: str, content: str, file_type: str, user_id: str) -> Document:
        normalized = content.replace("\x00", "").strip()
        if not normalized:
            raise ValueError("The uploaded document contains no extractable text")
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        doc = Document(filename=filename, content=normalized, file_type=file_type, content_hash=content_hash)
        self.repo.save_document(doc)
        chunks = chunk_document(doc)
        self.repo.save_chunks(chunks)
        self._audit(
            "document_ingested",
            user_id,
            document_id=str(doc.id),
            filename=filename,
            content_hash=content_hash,
            chunks=len(chunks),
        )
        return doc

    def generate_artifact(self, query: str, artifact_type: ArtifactType, user_id: str) -> Artifact:
        normalized_query = query.strip()
        if len(normalized_query) < 3:
            raise ValueError("Query must contain at least three characters")
        retrieved = retrieve_chunks(normalized_query, self.repo.get_all_chunks())
        artifact = build_artifact(artifact_type, retrieved, normalized_query)
        self.repo.save_artifact(artifact)
        self._audit(
            "artifact_generated",
            user_id,
            artifact_id=str(artifact.id),
            artifact_type=artifact_type.value,
            query=normalized_query,
            generator=artifact.generator,
            prompt_version=artifact.prompt_version,
            retrieved_chunk_ids=[str(chunk.id) for chunk in retrieved],
        )
        return artifact

    def edit_artifact(self, artifact_id: UUID, content: str, user_id: str) -> Optional[Artifact]:
        artifact = self.repo.get_artifact(artifact_id)
        if not artifact:
            return None
        if artifact.status == ArtifactStatus.EXPORTED:
            raise ValueError("Exported artifacts are immutable")
        normalized = content.strip()
        if not normalized:
            raise ValueError("Artifact content cannot be empty")
        artifact.content = normalized
        artifact.revision += 1
        artifact.status = ArtifactStatus.DRAFT
        artifact.reviewer_id = None
        artifact.review_comment = None
        artifact.updated_at = datetime.now(timezone.utc)
        self.repo.save_artifact(artifact)
        self._audit("artifact_edited", user_id, artifact_id=str(artifact.id), revision=artifact.revision)
        return artifact

    def update_artifact_status(
        self,
        artifact_id: UUID,
        status: ArtifactStatus,
        user_id: str,
        comment: Optional[str] = None,
    ) -> Optional[Artifact]:
        artifact = self.repo.get_artifact(artifact_id)
        if not artifact:
            return None
        allowed = {
            ArtifactStatus.DRAFT: {ArtifactStatus.APPROVED, ArtifactStatus.REJECTED},
            ArtifactStatus.REJECTED: {ArtifactStatus.APPROVED},
            ArtifactStatus.APPROVED: set(),
            ArtifactStatus.EXPORTED: set(),
        }
        if status not in allowed[artifact.status]:
            raise ValueError(f"Cannot transition artifact from {artifact.status.value} to {status.value}")
        if status == ArtifactStatus.APPROVED and not artifact.citations:
            raise ValueError("Artifacts without source citations cannot be approved")
        if status == ArtifactStatus.REJECTED and not (comment or "").strip():
            raise ValueError("A rejection comment is required")
        artifact.status = status
        artifact.reviewer_id = user_id
        artifact.review_comment = comment.strip() if comment else None
        artifact.updated_at = datetime.now(timezone.utc)
        self.repo.save_artifact(artifact)
        self._audit(
            "artifact_reviewed",
            user_id,
            artifact_id=str(artifact.id),
            new_status=status.value,
            comment=artifact.review_comment,
        )
        return artifact

    def export_artifact(self, artifact_id: UUID, target: str, user_id: str) -> ExportResult:
        artifact = self.repo.get_artifact(artifact_id)
        if not artifact or artifact.status != ArtifactStatus.APPROVED:
            raise ValueError("Only approved artifacts can be exported")
        normalized_target = target.lower().strip()
        if normalized_target not in {"json", "jira", "github"}:
            raise ValueError("target must be one of: json, jira, github")

        payload = self._export_payload(artifact, normalized_target)
        mode = "local"
        remote_url = None
        completed = normalized_target in {"json", "jira"}
        if normalized_target == "github":
            token = os.getenv("GITHUB_TOKEN")
            repository = os.getenv("GITHUB_REPOSITORY")
            allow_remote = os.getenv("AGENTIC_BA_ALLOW_REMOTE_EXPORT", "").lower() == "true"
            if allow_remote and token and repository:
                remote_url = self._create_github_issue(repository, token, payload)
                mode = "remote"
                completed = True
            else:
                mode = "preview"

        result = ExportResult(target=normalized_target, mode=mode, payload=payload, remote_url=remote_url)
        if completed:
            artifact.status = ArtifactStatus.EXPORTED
            artifact.updated_at = datetime.now(timezone.utc)
            self.repo.save_artifact(artifact)
        self._audit(
            "artifact_exported" if completed else "export_preview_created",
            user_id,
            artifact_id=str(artifact.id),
            target=normalized_target,
            mode=mode,
            remote_url=remote_url,
        )
        return result

    @staticmethod
    def _export_payload(artifact: Artifact, target: str) -> dict:
        citation_lines = [f"- chunk `{citation.chunk_id}`: “{citation.quote}”" for citation in artifact.citations]
        if target == "json":
            return {
                "id": str(artifact.id),
                "type": artifact.type.value,
                "content": artifact.content,
                "revision": artifact.revision,
                "citations": [citation.model_dump(mode="json") for citation in artifact.citations],
            }
        description = artifact.content + "\n\nSource evidence\n" + "\n".join(citation_lines)
        title = artifact.content.splitlines()[0][:100]
        if target == "jira":
            return {"fields": {"summary": title, "description": description, "issuetype": {"name": "Task"}}}
        return {"title": title, "body": description, "labels": ["source-backed", artifact.type.value]}

    @staticmethod
    def _create_github_issue(repository: str, token: str, payload: dict) -> str:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repository}/issues",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "agentic-ba-automation-platform",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
                return body["html_url"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"GitHub export failed: {exc}") from exc

    def seed_demo(self, user_id: str = "demo-analyst") -> dict:
        self.repo.reset()
        content = (
            "Customers need a guest checkout that accepts an email and delivery address. "
            "The checkout must show the full price before payment and preserve the basket if payment times out. "
            "Support agents need an order reference so they can investigate a failed payment."
        )
        document = self.process_document("checkout-discovery.md", content, "text/markdown", user_id)
        artifact = self.generate_artifact("guest checkout payment", ArtifactType.USER_STORY, user_id)
        return {"document": document, "artifact": artifact}

    def _audit(self, action: str, user_id: str, **details):
        self.repo.save_audit_log(AuditLog(action=action, user_id=user_id, details=details))
