from uuid import uuid4
from agentic_ba_automation_platform.domain.models import Document, Chunk, ArtifactType
from agentic_ba_automation_platform.algorithms.rag import chunk_document, retrieve_chunks
import pytest
from agentic_ba_automation_platform.algorithms.agent_layer import generate_artifact, generate_user_story, generate_acceptance_criteria
from agentic_ba_automation_platform.algorithms.document_worker import extract_text

def test_document_extraction():
    text = extract_text(b"Hello world", "text/plain")
    assert text == "Hello world"
    
    html_text = extract_text(b"<html><body><h1>Title</h1></body></html>", "text/html")
    assert html_text == "Title"

def test_chunking_and_retrieval():
    doc = Document(filename="test.txt", file_type="text/plain", content="This is a test document about the new login feature.")
    chunks = chunk_document(doc, chunk_size=20, overlap=5)
    assert len(chunks) > 0
    
    c1 = Chunk(document_id=uuid4(), content="login button requires email", start_index=0, end_index=20)
    c2 = Chunk(document_id=uuid4(), content="dashboard shows analytics", start_index=0, end_index=20)
    
    retrieved = retrieve_chunks("login email", [c1, c2])
    assert len(retrieved) == 1
    assert retrieved[0].content == "login button requires email"

def test_agent_generation():
    c = Chunk(document_id=uuid4(), content="login requires email", start_index=0, end_index=20)
    story = generate_user_story([c])
    assert story.type == ArtifactType.USER_STORY
    assert len(story.citations) == 1
    assert story.citations[0].chunk_id == c.id
    assert "login requires email" in story.content


@pytest.mark.parametrize("artifact_type", list(ArtifactType))
def test_every_artifact_type_is_grounded(artifact_type):
    chunk = Chunk(document_id=uuid4(), content="Customers need checkout totals before payment.", start_index=10, end_index=56)
    artifact = generate_artifact(artifact_type, [chunk], "checkout payment")
    assert artifact.content.strip()
    assert artifact.citations[0].quote in chunk.content
    assert artifact.query == "checkout payment"


def test_invalid_chunk_configuration_and_empty_evidence():
    document = Document(filename="test.txt", file_type="text/plain", content="evidence")
    with pytest.raises(ValueError):
        chunk_document(document, chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        generate_artifact(ArtifactType.RISK, [], "risk")
