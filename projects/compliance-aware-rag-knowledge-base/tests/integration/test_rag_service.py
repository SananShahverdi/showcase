from compliance_aware_rag_knowledge_base.adapters.repositories import AuditRepository, ChunkRepository, DocumentRepository, GovernanceRepository
from compliance_aware_rag_knowledge_base.domain.models import Document, DocumentStatus, GoldenQuestion, Query, RedactionRule, Role, Sensitivity
from compliance_aware_rag_knowledge_base.services.rag_service import RAGService


def service():
    return RAGService(DocumentRepository(), ChunkRepository(), AuditRepository(), GovernanceRepository())


def test_authorized_unauthorized_lifecycle_feedback_and_evaluation():
    rag = service()
    document = Document(title="Q1 Financials", content="Q1 revenue was 50 million dollars. Finance approved the result.", sensitivity=Sensitivity.CONFIDENTIAL, allowed_roles=[Role.EMPLOYEE], allowed_teams=["finance"])
    rag.ingest_document(document, actor_id="admin")

    unauthorized = rag.process_query(Query(user_id="contractor", user_role=Role.CONTRACTOR, user_teams=["finance"], clearance=Sensitivity.CONFIDENTIAL, text="What was Q1 revenue?"))
    assert unauthorized.abstained and not unauthorized.citations

    authorized = rag.process_query(Query(user_id="analyst", user_role=Role.EMPLOYEE, user_teams=["finance"], clearance=Sensitivity.CONFIDENTIAL, text="What was Q1 revenue?"))
    assert not authorized.abstained
    assert "50 million" in authorized.text
    assert authorized.citations[0].document_id == document.id
    feedback = rag.record_feedback(authorized.id, "analyst", 5, "Precise evidence")
    assert feedback.rating == 5

    rag.set_document_status(document.id, DocumentStatus.DELETED, "admin")
    assert rag.process_query(Query(user_id="analyst", user_role=Role.EMPLOYEE, user_teams=["finance"], clearance=Sensitivity.CONFIDENTIAL, text="What was Q1 revenue?")).abstained
    rag.set_document_status(document.id, DocumentStatus.ACTIVE, "admin")

    run = rag.run_evaluation([
        GoldenQuestion(question="What was Q1 revenue?", role=Role.EMPLOYEE, teams=["finance"], clearance=Sensitivity.CONFIDENTIAL, expected_keywords=["50 million"]),
        GoldenQuestion(question="What was Q1 revenue?", role=Role.CONTRACTOR, teams=["finance"], clearance=Sensitivity.CONFIDENTIAL, should_abstain=True),
    ], "admin")
    assert run.permission_leak_count == 0
    assert run.retrieval_hit_rate == 1
    assert run.abstention_accuracy == 1


def test_redaction_is_real_and_versioned():
    rag = service()
    rule = rag.save_redaction(RedactionRule(name="Email", pattern=r"[\w.+-]+@[\w.-]+", replacement="[EMAIL]"), "admin")
    assert rag.preview_redaction("Contact user@example.com", rule.pattern, rule.replacement) == "Contact [EMAIL]"
    document = Document(title="Contacts", content="Contact user@example.com for help.", allowed_roles=[Role.EMPLOYEE])
    rag.ingest_document(document, actor_id="admin")
    assert "[EMAIL]" in document.content
    assert "user@example.com" not in rag.chunk_repo.get_for_document(document.id)[0].content

