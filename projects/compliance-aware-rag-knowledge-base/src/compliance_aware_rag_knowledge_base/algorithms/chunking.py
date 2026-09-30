from __future__ import annotations

from typing import List

from compliance_aware_rag_knowledge_base.algorithms.retrieval import embed_text
from compliance_aware_rag_knowledge_base.domain.models import Chunk, Document


def chunk_document(document: Document, chunk_size: int = 700, overlap: int = 100) -> List[Chunk]:
    if chunk_size < 100:
        raise ValueError("chunk_size must be at least 100 characters")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    chunks: List[Chunk] = []
    text = document.content
    start = 0
    while start < len(text):
        proposed_end = min(start + chunk_size, len(text))
        end = proposed_end
        if proposed_end < len(text):
            boundary = max(text.rfind("\n", start, proposed_end), text.rfind(". ", start, proposed_end), text.rfind(" ", start, proposed_end))
            if boundary > start + chunk_size // 2:
                end = boundary + (1 if text[boundary:boundary + 2] == ". " else 0)
        content = text[start:end].strip()
        if content:
            actual_start = text.find(content, start, end + 1)
            actual_end = actual_start + len(content)
            chunks.append(
                Chunk(
                    document_id=document.id,
                    document_title=document.title,
                    content=content,
                    embedding=embed_text(content),
                    start_char=actual_start,
                    end_char=actual_end,
                    allowed_roles=document.allowed_roles,
                )
            )
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks
