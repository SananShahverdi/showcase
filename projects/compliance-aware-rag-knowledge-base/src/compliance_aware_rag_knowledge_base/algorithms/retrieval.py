from __future__ import annotations

from collections import Counter
from hashlib import sha256
from math import sqrt
import re
from typing import List, Tuple

from compliance_aware_rag_knowledge_base.domain.models import Chunk

TOKEN_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) > 1]


# Function words carry no evidence. Counting them let unrelated chunks pass the
# relevance threshold just by sharing "and", "the", or "who" with the question.
STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have how i if in into is it its "
    "me my of on or our so than that the their them then there these they this those to us was we were what "
    "when where which who whom whose why will with would you your".split()
)


def stem(token: str) -> str:
    """Tiny suffix stripper so "owns"/"owner" or "launch"/"launches" match."""
    for suffix in ("ing", "ers", "er", "es", "ed", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix) and not token.endswith("ss"):
            return token[: -len(suffix)]
    return token


def content_terms(text: str) -> List[str]:
    """Stemmed tokens without stopwords, used for lexical evidence."""
    return [stem(token) for token in tokenize(text) if token not in STOPWORDS]


def embed_text(text: str, dimensions: int = 64) -> List[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1 if digest[2] % 2 == 0 else -1
        vector[index] += sign * (1 + min(len(token), 12) / 12)
    norm = sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def cosine(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    raw = sum(a * b for a, b in zip(left, right))
    return max(0.0, min(1.0, (raw + 1) / 2))


def score_chunk(query: str, chunk: Chunk, alpha: float = 0.45) -> Tuple[float, float, float]:
    query_terms = content_terms(query)
    chunk_counts = Counter(content_terms(chunk.content))
    if not query_terms:
        lexical = 0.0
    else:
        matched = sum(min(1.0, chunk_counts[term] / 2) for term in set(query_terms))
        lexical = min(1.0, matched / len(set(query_terms)))
    query_embedding = embed_text(query)
    vector = cosine(query_embedding, chunk.embedding or embed_text(chunk.content))
    final = (1 - alpha) * lexical + alpha * vector
    return lexical, vector, final


def calculate_hybrid_score(query: str, chunk: Chunk, alpha: float = 0.45) -> float:
    return score_chunk(query, chunk, alpha)[2]


def rank_chunks(
    query: str,
    chunks: List[Chunk],
    top_k: int = 5,
    minimum_score: float = 0.30,
) -> List[Tuple[Chunk, float, float, float]]:
    scored = [(chunk, *score_chunk(query, chunk)) for chunk in chunks]
    scored = [item for item in scored if item[3] >= minimum_score]
    scored.sort(key=lambda item: (-item[3], str(item[0].id)))
    return scored[:top_k]
