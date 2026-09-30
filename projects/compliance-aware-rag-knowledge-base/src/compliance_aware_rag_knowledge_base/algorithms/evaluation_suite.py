from typing import List, Dict, Any
from compliance_aware_rag_knowledge_base.domain.models import Answer, Chunk
from compliance_aware_rag_knowledge_base.algorithms.evaluation import detect_unsupported_claims, validate_citation_coverage

def evaluate_retrieval_quality(retrieved_chunks: List[Chunk], ground_truth_keywords: List[str]) -> float:
    """Calculates recall-like score based on ground truth keywords found in retrieved chunks."""
    if not ground_truth_keywords:
        return 1.0
    found_keywords = 0
    all_text = " ".join([c.content.lower() for c in retrieved_chunks])
    for kw in ground_truth_keywords:
        if kw.lower() in all_text:
            found_keywords += 1
    return found_keywords / len(ground_truth_keywords)

def evaluate_answer(answer: Answer, retrieved_chunks: List[Chunk], ground_truth_keywords: List[str] = None) -> Dict[str, Any]:
    """Runs a full suite of evaluations on an answer."""
    unsupported = detect_unsupported_claims(answer, retrieved_chunks)
    has_citations = validate_citation_coverage(answer)
    retrieval_score = evaluate_retrieval_quality(retrieved_chunks, ground_truth_keywords or [])
    
    return {
        "citation_coverage": has_citations,
        "hallucination_detected": unsupported,
        "retrieval_quality_score": retrieval_score,
        "overall_quality": "FAIL" if (unsupported or not has_citations) else "PASS"
    }
