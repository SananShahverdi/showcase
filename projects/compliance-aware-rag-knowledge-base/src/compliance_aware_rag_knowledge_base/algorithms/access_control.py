from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from compliance_aware_rag_knowledge_base.domain.models import (
    Chunk,
    Document,
    DocumentStatus,
    Query,
    Role,
    Sensitivity,
    utc_now,
)

SENSITIVITY_ORDER = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
}


def evaluate_document_access(document: Document, query: Query, now: datetime | None = None) -> Tuple[bool, str]:
    current = now or utc_now()
    if document.status != DocumentStatus.ACTIVE:
        return False, "inactive"
    if document.expires_at and document.expires_at <= current:
        return False, "expired"
    if SENSITIVITY_ORDER[query.clearance] < SENSITIVITY_ORDER[document.sensitivity]:
        return False, "insufficient_clearance"
    if query.user_role == Role.ADMIN:
        return True, "admin_override"
    if query.user_role not in document.allowed_roles:
        return False, "role_denied"
    if document.allowed_teams and not set(query.user_teams).intersection(document.allowed_teams):
        return False, "team_denied"
    return True, "allowed"


def filter_chunks_by_role(chunks: List[Chunk], user_role: Role) -> List[Chunk]:
    return [chunk for chunk in chunks if user_role == Role.ADMIN or user_role in chunk.allowed_roles]
