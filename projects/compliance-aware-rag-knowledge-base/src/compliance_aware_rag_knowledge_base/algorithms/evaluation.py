from typing import List

from compliance_aware_rag_knowledge_base.domain.models import Answer, Chunk


def validate_citation_coverage(answer: Answer) -> bool:
    if answer.abstained:
        return not answer.citations
    return bool(answer.text.strip()) and bool(answer.citations)


def detect_unsupported_claims(answer: Answer, retrieved_chunks: List[Chunk]) -> bool:
    chunk_map = {chunk.id: chunk for chunk in retrieved_chunks}
    if answer.abstained:
        return bool(answer.citations)
    if not answer.citations:
        return True
    for citation in answer.citations:
        chunk = chunk_map.get(citation.chunk_id)
        if chunk is None or citation.quote not in chunk.content:
            return True
        if citation.document_id != chunk.document_id:
            return True
    return False
