from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional
from uuid import UUID

from compliance_aware_rag_knowledge_base.domain.models import (
    AuditEvent,
    Chunk,
    Document,
    EvaluationRun,
    Feedback,
    RedactionRule,
)


class _JsonRepository:
    model = None
    env_name = ""
    filename = "state.json"

    def __init__(self) -> None:
        state_dir = os.getenv("RAG_STATE_DIR", "")
        self._path = Path(state_dir) / self.filename if state_dir else None
        self._lock = RLock()

    def _read(self) -> list:
        if self._path is None or not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, items: list) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps(items, indent=2), encoding="utf-8")
        temporary.replace(self._path)


class DocumentRepository(_JsonRepository):
    filename = "documents.json"

    def __init__(self) -> None:
        super().__init__()
        self.docs: Dict[UUID, Document] = {UUID(item["id"]): Document.model_validate(item) for item in self._read()}

    def _persist(self) -> None:
        self._write([item.model_dump(mode="json") for item in self.docs.values()])

    def save(self, document: Document) -> Document:
        with self._lock:
            self.docs[document.id] = document
            self._persist()
        return document

    def get(self, document_id: UUID) -> Optional[Document]:
        return self.docs.get(document_id)

    def get_all(self) -> List[Document]:
        return sorted(self.docs.values(), key=lambda item: item.created_at, reverse=True)


class ChunkRepository(_JsonRepository):
    filename = "chunks.json"

    def __init__(self) -> None:
        super().__init__()
        self.chunks: Dict[UUID, Chunk] = {UUID(item["id"]): Chunk.model_validate(item) for item in self._read()}

    def _persist(self) -> None:
        self._write([item.model_dump(mode="json") for item in self.chunks.values()])

    def save_all(self, chunks: List[Chunk]) -> None:
        with self._lock:
            for chunk in chunks:
                self.chunks[chunk.id] = chunk
            self._persist()

    def replace_document_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None:
        with self._lock:
            self.chunks = {key: value for key, value in self.chunks.items() if value.document_id != document_id}
            for chunk in chunks:
                self.chunks[chunk.id] = chunk
            self._persist()

    def get_all(self) -> List[Chunk]:
        return list(self.chunks.values())

    def get_for_document(self, document_id: UUID) -> List[Chunk]:
        return [item for item in self.chunks.values() if item.document_id == document_id]


class AuditRepository(_JsonRepository):
    filename = "audit.json"

    def __init__(self) -> None:
        super().__init__()
        self.events: List[AuditEvent] = [AuditEvent.model_validate(item) for item in self._read()]

    def save(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            self.events.append(event)
            self._write([item.model_dump(mode="json") for item in self.events])
        return event

    def get_all(self) -> List[AuditEvent]:
        return sorted(self.events, key=lambda item: item.timestamp, reverse=True)


class GovernanceRepository(_JsonRepository):
    filename = "governance.json"

    def __init__(self) -> None:
        super().__init__()
        payload = self._read()
        state = payload[0] if payload else {}
        self.redaction_rules: Dict[UUID, RedactionRule] = {
            UUID(item["id"]): RedactionRule.model_validate(item) for item in state.get("redaction_rules", [])
        }
        self.feedback: List[Feedback] = [Feedback.model_validate(item) for item in state.get("feedback", [])]
        self.evaluations: List[EvaluationRun] = [EvaluationRun.model_validate(item) for item in state.get("evaluations", [])]

    def _persist(self) -> None:
        self._write([{
            "redaction_rules": [item.model_dump(mode="json") for item in self.redaction_rules.values()],
            "feedback": [item.model_dump(mode="json") for item in self.feedback],
            "evaluations": [item.model_dump(mode="json") for item in self.evaluations],
        }])

    def save_redaction(self, rule: RedactionRule) -> RedactionRule:
        with self._lock:
            existing = self.redaction_rules.get(rule.id)
            if existing:
                rule.version = existing.version + 1
            self.redaction_rules[rule.id] = rule
            self._persist()
        return rule

    def list_redactions(self) -> List[RedactionRule]:
        return list(self.redaction_rules.values())

    def save_feedback(self, feedback: Feedback) -> Feedback:
        with self._lock:
            self.feedback.append(feedback)
            self._persist()
        return feedback

    def list_feedback(self) -> List[Feedback]:
        return list(self.feedback)

    def save_evaluation(self, run: EvaluationRun) -> EvaluationRun:
        with self._lock:
            self.evaluations.append(run)
            self._persist()
        return run

    def list_evaluations(self) -> List[EvaluationRun]:
        return sorted(self.evaluations, key=lambda item: item.created_at, reverse=True)


# Backward-compatible names keep existing service-level consumers working while
# production routes use the storage-neutral names above.
InMemoryDocumentRepository = DocumentRepository
InMemoryChunkRepository = ChunkRepository
InMemoryAuditRepository = AuditRepository
