import re
from collections import Counter
from typing import List
from agentic_ba_automation_platform.domain.models import Document, Chunk

def chunk_document(document: Document, chunk_size: int = 1000, overlap: int = 100) -> List[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size - 1")
    chunks = []
    text = document.content
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        chunks.append(Chunk(document_id=document.id, content=chunk_text, start_index=start, end_index=start+len(chunk_text)))
        start += (chunk_size - overlap)
    return chunks

def retrieve_chunks(query: str, all_chunks: List[Chunk], top_k: int = 3) -> List[Chunk]:
    """Rank chunks with a deterministic lexical score and stable tie breaking."""
    query_words = [word for word in re.findall(r"[a-z0-9]+", query.lower()) if len(word) > 1]
    if not query_words or top_k <= 0:
        return []
    query_counts = Counter(query_words)
    
    def score_chunk(chunk: Chunk) -> float:
        chunk_words = re.findall(r"[a-z0-9]+", chunk.content.lower())
        counts = Counter(chunk_words)
        coverage = sum(min(counts[word], count) for word, count in query_counts.items())
        phrase_bonus = 2 if " ".join(query_words) in " ".join(chunk_words) else 0
        return coverage + phrase_bonus + (coverage / max(len(chunk_words), 1))
    
    scored = [(c, score_chunk(c)) for c in all_chunks]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: (-x[1], x[0].start_index, str(x[0].id)))
    return [c for c, s in scored[:top_k]]
