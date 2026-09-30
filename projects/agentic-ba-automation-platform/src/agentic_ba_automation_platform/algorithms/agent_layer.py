"""Deterministic, source-grounded artifact generation for the offline product path.

This module intentionally does not pretend to be an LLM.  A hosted/local model can
be added behind the same service boundary, but citations are always constructed
from stored chunks and verified here.
"""

import re
from typing import Callable, Dict, List

from agentic_ba_automation_platform.domain.models import Artifact, ArtifactType, Chunk, Citation


def _sentences(chunks: List[Chunk]) -> List[str]:
    text = " ".join(chunk.content.strip() for chunk in chunks)
    values = [re.sub(r"\s+", " ", item).strip(" -\t") for item in re.split(r"(?<=[.!?])\s+|\n+", text)]
    return [value for value in values if len(value) >= 8][:8]


def _citations(chunks: List[Chunk]) -> List[Citation]:
    citations: List[Citation] = []
    for chunk in chunks:
        quote = re.sub(r"\s+", " ", chunk.content).strip()[:240]
        if quote:
            citations.append(
                Citation(
                    chunk_id=chunk.id,
                    quote=quote,
                    start_index=chunk.start_index,
                    end_index=chunk.start_index + len(quote),
                )
            )
    return citations


def _subject(sentences: List[str]) -> str:
    if not sentences:
        return "the documented requirement"
    return sentences[0].rstrip(".")


def _user_story(sentences: List[str]) -> str:
    fact = _subject(sentences)
    role_match = re.search(r"\b(customer|user|agent|administrator|admin|manager|analyst|operator)\b", fact, re.I)
    role = role_match.group(1).lower() if role_match else "product user"
    return f"As a {role}, I want the product to satisfy this source requirement: {fact}, so that the documented stakeholder need is delivered and testable."


def _acceptance_criteria(sentences: List[str]) -> str:
    lines = []
    for index, fact in enumerate(sentences[:4], 1):
        lines.append(f"{index}. Given the documented context, when the related workflow is used, then the system must satisfy: {fact.rstrip('.')}.")
    return "\n".join(lines)


def _risks(sentences: List[str]) -> str:
    fact = _subject(sentences)
    return "\n".join([
        f"1. Requirement ambiguity — The phrase “{fact[:120]}” may admit multiple interpretations. Mitigation: confirm measurable outcomes with the product owner.",
        "2. Failure-path coverage — The evidence may describe the happy path only. Mitigation: add unavailable, invalid-input, timeout, and retry acceptance cases.",
        "3. Traceability drift — Later edits may weaken source alignment. Mitigation: re-check citations on every revision before approval.",
    ])


def _assumptions(sentences: List[str]) -> str:
    evidence = sentences[:3] or ["No additional source statement was available"]
    return "\n".join(f"{index}. Assumption to validate: {fact.rstrip('.')}." for index, fact in enumerate(evidence, 1))


def _process_summary(sentences: List[str]) -> str:
    steps = sentences[:5]
    return "Process derived from the supplied evidence:\n" + "\n".join(
        f"{index}. {fact.rstrip('.')}" for index, fact in enumerate(steps, 1)
    )


def _implementation_ticket(sentences: List[str]) -> str:
    fact = _subject(sentences)
    supporting = sentences[1:4]
    details = "\n".join(f"- {item.rstrip('.')}" for item in supporting) or "- Preserve the cited behavior exactly."
    return (
        f"Title: Implement {fact[:100]}\n\n"
        f"Objective\nDeliver the cited requirement: {fact}.\n\n"
        f"Source-backed constraints\n{details}\n\n"
        "Definition of done\n- Automated tests cover the normal and failure paths.\n"
        "- The implemented behavior can be traced to the attached source chunks.\n"
        "- Observability and operator-facing errors are included."
    )


GENERATORS: Dict[ArtifactType, Callable[[List[str]], str]] = {
    ArtifactType.USER_STORY: _user_story,
    ArtifactType.ACCEPTANCE_CRITERIA: _acceptance_criteria,
    ArtifactType.RISK: _risks,
    ArtifactType.ASSUMPTION: _assumptions,
    ArtifactType.PROCESS_SUMMARY: _process_summary,
    ArtifactType.IMPLEMENTATION_TICKET: _implementation_ticket,
}


def generate_artifact(artifact_type: ArtifactType, chunks: List[Chunk], query: str = "") -> Artifact:
    if not chunks:
        raise ValueError("No supporting source chunks matched this request")
    content = GENERATORS[artifact_type](_sentences(chunks))
    return Artifact(type=artifact_type, content=content, citations=_citations(chunks), query=query)


def generate_user_story(chunks: List[Chunk]) -> Artifact:
    return generate_artifact(ArtifactType.USER_STORY, chunks)


def generate_acceptance_criteria(chunks: List[Chunk]) -> Artifact:
    return generate_artifact(ArtifactType.ACCEPTANCE_CRITERIA, chunks)


def generate_implementation_ticket(chunks: List[Chunk]) -> Artifact:
    return generate_artifact(ArtifactType.IMPLEMENTATION_TICKET, chunks)
