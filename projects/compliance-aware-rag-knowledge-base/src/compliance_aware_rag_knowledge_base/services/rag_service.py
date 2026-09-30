from __future__ import annotations

from collections import Counter
from datetime import timedelta
import re
import time
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from compliance_aware_rag_knowledge_base.adapters.repositories import (
    AuditRepository,
    ChunkRepository,
    DocumentRepository,
    GovernanceRepository,
)
from compliance_aware_rag_knowledge_base.algorithms.access_control import evaluate_document_access
from compliance_aware_rag_knowledge_base.algorithms.chunking import chunk_document
from compliance_aware_rag_knowledge_base.algorithms.evaluation import detect_unsupported_claims, validate_citation_coverage
from compliance_aware_rag_knowledge_base.algorithms.retrieval import content_terms, rank_chunks
from compliance_aware_rag_knowledge_base.domain.models import (
    Answer,
    AuditEvent,
    AuditEventType,
    Citation,
    Document,
    DocumentStatus,
    DocumentUpdate,
    EvaluationRun,
    Feedback,
    GoldenQuestion,
    Query,
    RedactionRule,
    utc_now,
)


class RAGService:
    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        audit_repo: AuditRepository,
        governance_repo: Optional[GovernanceRepository] = None,
    ) -> None:
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo
        self.audit_repo = audit_repo
        self.governance_repo = governance_repo or GovernanceRepository()
        self.answers: Dict[UUID, Answer] = {}

    def _audit(self, event_type: AuditEventType, actor_id: Optional[str], details: dict, request_id: Optional[str] = None) -> None:
        self.audit_repo.save(AuditEvent(event_type=event_type, actor_id=actor_id, request_id=request_id, details=details))

    def _apply_redactions(self, text: str, ingestion: bool = False, audit: bool = False) -> str:
        result = text
        for rule in self.governance_repo.list_redactions():
            if rule.enabled and ((ingestion and rule.apply_to_ingestion) or (audit and rule.apply_to_audit)):
                result = re.sub(rule.pattern, rule.replacement, result)
        return result

    def ingest_document(self, document: Document, chunk_size: int = 700, overlap: int = 100, actor_id: str = "system") -> List:
        document.content = self._apply_redactions(document.content, ingestion=True)
        self.doc_repo.save(document)
        chunks = chunk_document(document, chunk_size, overlap)
        self.chunk_repo.replace_document_chunks(document.id, chunks)
        self._audit(
            AuditEventType.DOCUMENT_INGESTED,
            actor_id,
            {
                "document_id": str(document.id), "title": document.title, "checksum_sha256": document.checksum_sha256,
                "parser": document.parser, "chunk_count": len(chunks), "version": document.version,
                "classification": document.sensitivity.value, "allowed_roles": [role.value for role in document.allowed_roles],
                "allowed_teams": document.allowed_teams, "expires_at": document.expires_at.isoformat() if document.expires_at else None,
            },
        )
        return chunks

    def process_query(self, query: Query, request_id: Optional[str] = None) -> Answer:
        started = time.perf_counter()
        safe_query = self._apply_redactions(query.text, audit=True)
        self._audit(
            AuditEventType.QUERY_SUBMITTED, query.user_id,
            {"query_id": str(query.id), "query": safe_query, "role": query.user_role.value, "teams": query.user_teams, "clearance": query.clearance.value},
            request_id,
        )
        permitted_ids = set()
        decisions = Counter()
        for document in self.doc_repo.get_all():
            allowed, reason = evaluate_document_access(document, query)
            decisions[reason] += 1
            if allowed:
                permitted_ids.add(document.id)
        candidates = [chunk for chunk in self.chunk_repo.get_all() if chunk.document_id in permitted_ids]
        ranked = rank_chunks(query.text, candidates, top_k=query.top_k)
        answer = self._grounded_answer(query, ranked)
        retrieved = [item[0] for item in ranked]
        unsupported = detect_unsupported_claims(answer, retrieved)
        citation_valid = validate_citation_coverage(answer)
        if unsupported or not citation_valid:
            answer.low_confidence = True
            answer.confidence_score = min(answer.confidence_score, 0.25)
        self.answers[answer.id] = answer
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        self._audit(
            AuditEventType.ANSWER_GENERATED, query.user_id,
            {
                "query_id": str(query.id), "answer_id": str(answer.id), "answer": self._apply_redactions(answer.text, audit=True),
                "abstained": answer.abstained, "confidence_score": answer.confidence_score,
                "policy_decisions": dict(decisions), "candidate_count_after_policy": len(candidates),
                "retrieved": [
                    {"chunk_id": str(chunk.id), "document_id": str(chunk.document_id), "lexical_score": lexical, "vector_score": vector, "final_score": final}
                    for chunk, lexical, vector, final in ranked
                ],
                "citations": [citation.model_dump(mode="json") for citation in answer.citations],
                "model": answer.model, "prompt_version": answer.prompt_version, "latency_ms": elapsed_ms,
            }, request_id,
        )
        if not permitted_ids and self.doc_repo.get_all():
            self._audit(AuditEventType.POLICY_DENIED, query.user_id, {"query_id": str(query.id), "decision_counts": dict(decisions)}, request_id)
        return answer

    @staticmethod
    def _best_quote(query: str, content: str, limit: int = 320) -> str:
        """The most relevant sentence, extended to neighbours that cover more of the question.

        The quote is always one contiguous span of the chunk, so it can be verified
        verbatim; a two-part question ("when ... and who ...") can draw on adjacent sentences.
        """
        terms = set(content_terms(query))
        # Sentence ends are punctuation followed by whitespace, so "2.4" stays intact.
        cuts = [0] + [point for match in re.finditer(r"(?<=[.!?])\s+|\n+", content) for point in (match.start(), match.end())] + [len(content)]
        spans = [(start, end) for start, end in zip(cuts[::2], cuts[1::2]) if content[start:end].strip()]
        if not spans:
            return content[:limit]
        covered = [terms.intersection(content_terms(content[start:end])) for start, end in spans]
        best = max(range(len(spans)), key=lambda index: len(covered[index]))
        first = last = best
        seen = set(covered[best])
        for step in (1, -1):
            index = best + step
            while 0 <= index < len(spans) and covered[index] - seen:
                if spans[max(index, last)][1] - spans[min(index, first)][0] > limit:
                    break
                seen |= covered[index]
                first, last = min(first, index), max(last, index)
                index += step
        quote = content[spans[first][0]:spans[last][1]].strip()
        return quote[:limit].rstrip()

    def _grounded_answer(self, query: Query, ranked: List[Tuple]) -> Answer:
        if not ranked:
            return Answer(
                query_id=query.id,
                text="I could not find permitted evidence relevant enough to answer this question.",
                citations=[], confidence_score=0, low_confidence=True, abstained=True,
            )
        citations: List[Citation] = []
        extracts: List[str] = []
        for chunk, lexical, vector, final in ranked[:3]:
            quote = self._best_quote(query.text, chunk.content)
            local_start = chunk.content.find(quote)
            start = chunk.start_char + max(local_start, 0)
            extracts.append(quote)
            citations.append(
                Citation(
                    chunk_id=chunk.id, document_id=chunk.document_id, document_title=chunk.document_title,
                    quote=quote, start_char=start, end_char=start + len(quote),
                    lexical_score=round(lexical, 4), vector_score=round(vector, 4), relevance_score=round(final, 4),
                )
            )
        confidence = sum(item[3] for item in ranked[:3]) / min(3, len(ranked))
        return Answer(
            query_id=query.id,
            text="\n\n".join(extracts),
            citations=citations,
            confidence_score=round(confidence, 4),
            low_confidence=confidence < 0.5,
        )

    def update_document(self, document_id: UUID, update: DocumentUpdate, actor_id: str) -> Document:
        document = self._document(document_id)
        changes = update.model_dump(exclude_none=True)
        for key, value in changes.items():
            setattr(document, key, value)
        if update.retention_days is not None:
            document.expires_at = document.created_at + timedelta(days=update.retention_days)
        document.version += 1
        document.updated_at = utc_now()
        self.doc_repo.save(document)
        self.chunk_repo.replace_document_chunks(document.id, chunk_document(document))
        self._audit(AuditEventType.DOCUMENT_UPDATED, actor_id, {"document_id": str(document.id), "version": document.version, "changed_fields": sorted(changes)})
        return document

    def set_document_status(self, document_id: UUID, status: DocumentStatus, actor_id: str) -> Document:
        document = self._document(document_id)
        document.status = status
        document.updated_at = utc_now()
        document.version += 1
        self.doc_repo.save(document)
        event = AuditEventType.DOCUMENT_DELETED if status == DocumentStatus.DELETED else AuditEventType.DOCUMENT_RESTORED
        self._audit(event, actor_id, {"document_id": str(document.id), "version": document.version})
        return document

    def retention_preview(self) -> List[Document]:
        now = utc_now()
        return [document for document in self.doc_repo.get_all() if document.status == DocumentStatus.ACTIVE and document.expires_at and document.expires_at <= now]

    def enforce_retention(self, actor_id: str) -> List[Document]:
        expired = self.retention_preview()
        for document in expired:
            document.status = DocumentStatus.DELETED
            document.updated_at = utc_now()
            document.version += 1
            self.doc_repo.save(document)
        self._audit(AuditEventType.RETENTION_ENFORCED, actor_id, {"expired_document_ids": [str(item.id) for item in expired], "count": len(expired)})
        return expired

    @staticmethod
    def validate_redaction_pattern(pattern: str) -> None:
        if re.search(r"(\([^)]*[+*][^)]*\))[+*]", pattern):
            raise ValueError("Nested repetition is not allowed in redaction patterns")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid redaction pattern: {exc.msg}") from exc

    def save_redaction(self, rule: RedactionRule, actor_id: str) -> RedactionRule:
        self.validate_redaction_pattern(rule.pattern)
        stored = self.governance_repo.save_redaction(rule)
        self._audit(AuditEventType.REDACTION_CHANGED, actor_id, {"rule_id": str(rule.id), "name": rule.name, "version": rule.version, "enabled": rule.enabled})
        return stored

    def preview_redaction(self, text: str, pattern: str, replacement: str) -> str:
        self.validate_redaction_pattern(pattern)
        return re.sub(pattern, replacement, text[:10_000])

    def record_feedback(self, answer_id: UUID, user_id: str, rating: int, reason: str) -> Feedback:
        if answer_id not in self.answers:
            raise ValueError("Answer not found in this service session")
        feedback = self.governance_repo.save_feedback(Feedback(answer_id=answer_id, user_id=user_id, rating=rating, reason=reason))
        self._audit(AuditEventType.FEEDBACK_RECORDED, user_id, {"answer_id": str(answer_id), "feedback_id": str(feedback.id), "rating": rating, "reason": self._apply_redactions(reason, audit=True)})
        return feedback

    def run_evaluation(self, questions: List[GoldenQuestion], actor_id: str) -> EvaluationRun:
        if not questions:
            raise ValueError("At least one golden question is required")
        cases = []
        hits = citations_valid = abstention_correct = leakage = 0
        latencies = []
        for index, golden in enumerate(questions):
            query = Query(
                user_id=f"evaluation-{index}", user_role=golden.role, user_teams=golden.teams,
                clearance=golden.clearance, text=golden.question,
            )
            started = time.perf_counter()
            answer = self.process_query(query)
            latencies.append((time.perf_counter() - started) * 1000)
            answer_text = answer.text.lower()
            hit = all(keyword.lower() in answer_text for keyword in golden.expected_keywords)
            valid = validate_citation_coverage(answer)
            abstention_ok = answer.abstained == golden.should_abstain
            permission_leak = False
            for citation in answer.citations:
                document = self.doc_repo.get(citation.document_id)
                if document and not evaluate_document_access(document, query)[0]:
                    permission_leak = True
            hits += int(hit)
            citations_valid += int(valid)
            abstention_correct += int(abstention_ok)
            leakage += int(permission_leak)
            cases.append({"question": golden.question, "hit": hit, "citation_valid": valid, "abstention_correct": abstention_ok, "permission_leak": permission_leak, "answer_id": str(answer.id)})
        count = len(questions)
        run = EvaluationRun(
            question_count=count,
            retrieval_hit_rate=round(hits / count, 4),
            citation_validity_rate=round(citations_valid / count, 4),
            abstention_accuracy=round(abstention_correct / count, 4),
            permission_leak_count=leakage,
            average_latency_ms=round(sum(latencies) / count, 3),
            overall_status="PASS" if leakage == 0 and hits / count >= 0.8 and citations_valid / count == 1 else "FAIL",
            cases=cases,
        )
        self.governance_repo.save_evaluation(run)
        self._audit(AuditEventType.EVALUATION_RUN, actor_id, run.model_dump(mode="json"))
        return run

    def _document(self, document_id: UUID) -> Document:
        document = self.doc_repo.get(document_id)
        if document is None:
            raise ValueError("Document not found")
        return document
