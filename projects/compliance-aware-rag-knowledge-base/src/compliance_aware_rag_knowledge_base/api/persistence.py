"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from compliance_aware_rag_knowledge_base.adapters.database import Binding, StatePersistence
from compliance_aware_rag_knowledge_base.api import routes
from compliance_aware_rag_knowledge_base.domain.models import Answer, AuditEvent, Chunk, Document, EvaluationRun, Feedback, RedactionRule


NAMESPACE = "compliance_aware_rag_knowledge_base"


def bindings() -> list:
    return [
        Binding("documents", lambda: routes.doc_repo.docs, Document, UUID),
        Binding("chunks", lambda: routes.chunk_repo.chunks, Chunk, UUID),
        Binding("audit", lambda: routes.audit_repo.events, AuditEvent),
        Binding("redaction_rules", lambda: routes.governance_repo.redaction_rules, RedactionRule, UUID),
        Binding("feedback", lambda: routes.governance_repo.feedback, Feedback),
        Binding("evaluations", lambda: routes.governance_repo.evaluations, EvaluationRun),
        Binding("answers", lambda: routes.rag_service.answers, Answer, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
