from datetime import timedelta
from uuid import uuid4

import pytest

from compliance_aware_rag_knowledge_base.algorithms.access_control import evaluate_document_access
from compliance_aware_rag_knowledge_base.algorithms.chunking import chunk_document
from compliance_aware_rag_knowledge_base.algorithms.evaluation import detect_unsupported_claims, validate_citation_coverage
from compliance_aware_rag_knowledge_base.algorithms.ingestion import DocumentParseError, extract_text
from compliance_aware_rag_knowledge_base.algorithms.retrieval import calculate_hybrid_score, embed_text, rank_chunks
from compliance_aware_rag_knowledge_base.domain.models import Answer, Citation, Document, Query, Role, Sensitivity, utc_now


def document(**overrides):
    values = {"title": "Launch brief", "content": "Project Atlas launches in Q3 2026. Maya owns the launch.", "allowed_roles": [Role.EMPLOYEE], "allowed_teams": ["product"]}
    values.update(overrides)
    return Document(**values)


def test_chunking_has_stable_offsets_embeddings_and_validates_window():
    doc = document(content=("A governed knowledge sentence with useful evidence. " * 40).strip())
    chunks = chunk_document(doc, chunk_size=180, overlap=30)
    assert len(chunks) > 2
    assert all(doc.content[item.start_char:item.end_char] == item.content for item in chunks)
    assert all(len(item.embedding) == 64 for item in chunks)
    with pytest.raises(ValueError, match="overlap"):
        chunk_document(doc, chunk_size=100, overlap=100)


def test_policy_enforces_status_expiry_role_team_and_clearance_before_retrieval():
    doc = document(sensitivity=Sensitivity.CONFIDENTIAL)
    allowed = Query(user_id="u", user_role=Role.EMPLOYEE, user_teams=["product"], clearance=Sensitivity.CONFIDENTIAL, text="Atlas launch")
    assert evaluate_document_access(doc, allowed) == (True, "allowed")
    assert evaluate_document_access(doc, allowed.model_copy(update={"user_teams": ["finance"]}))[1] == "team_denied"
    assert evaluate_document_access(doc, allowed.model_copy(update={"user_role": Role.CONTRACTOR}))[1] == "role_denied"
    assert evaluate_document_access(doc, allowed.model_copy(update={"clearance": Sensitivity.INTERNAL}))[1] == "insufficient_clearance"
    doc.expires_at = utc_now() - timedelta(seconds=1)
    assert evaluate_document_access(doc, allowed)[1] == "expired"


def test_hybrid_retrieval_exposes_real_lexical_and_vector_components():
    doc = document()
    relevant = chunk_document(doc)[0]
    unrelated_doc = document(title="Catering", content="The cafeteria serves soup on Tuesday.")
    unrelated = chunk_document(unrelated_doc)[0]
    ranked = rank_chunks("When does Atlas launch?", [unrelated, relevant], minimum_score=0.25)
    assert ranked[0][0].id == relevant.id
    assert ranked[0][1] > 0
    assert 0 <= ranked[0][2] <= 1
    assert calculate_hybrid_score("Atlas launch", relevant) > calculate_hybrid_score("Atlas launch", unrelated)


def test_citation_validation_requires_exact_retrieved_quote():
    chunk = chunk_document(document())[0]
    citation = Citation(chunk_id=chunk.id, document_id=chunk.document_id, document_title=chunk.document_title, quote="Project Atlas launches in Q3 2026.", start_char=0, end_char=35, lexical_score=.8, vector_score=.7, relevance_score=.75)
    answer = Answer(query_id=uuid4(), text=citation.quote, citations=[citation], confidence_score=.75)
    assert validate_citation_coverage(answer)
    assert not detect_unsupported_claims(answer, [chunk])
    tampered = answer.model_copy(update={"citations": [citation.model_copy(update={"quote": "Unsupported claim"})]})
    assert detect_unsupported_claims(tampered, [chunk])


def test_parsers_strip_active_html_and_reject_unsupported_or_empty_files():
    assert extract_text(b"<h1>Policy</h1><script>steal()</script><p>Approved</p>", "text/html", "policy.html") == "Policy Approved"
    assert extract_text(b"# Heading\nUseful **evidence**", "text/markdown", "readme.md") == "Heading Useful evidence"
    with pytest.raises(DocumentParseError, match="Unsupported"):
        extract_text(b"binary", "image/png", "image.png")
    with pytest.raises(DocumentParseError, match="no extractable"):
        extract_text(b"   ", "text/plain", "empty.txt")


def test_stopwords_alone_do_not_make_a_chunk_relevant():
    from compliance_aware_rag_knowledge_base.algorithms.retrieval import content_terms, score_chunk
    assert content_terms("When does Project Atlas launch and who owns it?") == content_terms("project atlas launches own")
    onboarding = chunk_document(document(title="Onboarding", content="Contractors receive access after approval and training."))[0]
    lexical, _, _ = score_chunk("When does Atlas launch and who owns it?", onboarding)
    assert lexical == 0


def test_quote_is_contiguous_and_covers_multi_part_questions():
    from compliance_aware_rag_knowledge_base.services.rag_service import RAGService
    content = "Project Atlas launches in Q3 2026. The launch owner is Maya Chen. The approved launch budget is 2.4 million dollars."
    quote = RAGService._best_quote("When does Project Atlas launch and who owns it?", content)
    assert quote == "Project Atlas launches in Q3 2026. The launch owner is Maya Chen."
    assert quote in content
    # Decimal points are not sentence boundaries.
    assert RAGService._best_quote("What is the budget?", content) == "The approved launch budget is 2.4 million dollars."
