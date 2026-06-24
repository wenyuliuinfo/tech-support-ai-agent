"""Service-level tests with mocked repositories."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from repositories.openai_repo import ChatChunk
from repositories.pinecone import ChunkResult
from repositories.ticket import TicketRecord
from services.chat import ChatService

ACCOUNT_ID = uuid4()


@pytest.fixture
def sample_chunks():
    return [
        ChunkResult(
            chunk_id="doc1_0_abc123",
            document_id="doc1",
            source_path="docs/knowledge_base/test.md",
            file_name="test.md",
            chunk_index=0,
            content="To enable replication, go to Settings > Replication.",
            title="VMware Replication Setup",
            section_heading="Enabling Replication",
            score=0.95,
        )
    ]


@pytest.fixture
def sample_tickets():
    return [
        TicketRecord(
            ticket_number="T-001",
            account_id=ACCOUNT_ID,
            subject="Replication not working",
            status="closed",
            created_at="2026-03-19",
            resolution="Enabled replication from portal",
        )
    ]


class TestChatService:
    @pytest.mark.asyncio
    async def test_stream_answer_emits_citation_then_token_then_done(
        self, sample_chunks, sample_tickets
    ):
        service = ChatService()

        async def mock_embed(text):
            return [0.1] * 1024

        async def mock_query(embedding, top_k=5, min_score=0.0):
            return sample_chunks

        async def mock_search(account_id, query, limit=3):
            return sample_tickets

        async def mock_stream(messages, temperature=0.3, max_tokens=1024):
            yield ChatChunk(content="Here is how", finish_reason=None)
            yield ChatChunk(content=" you do it.", finish_reason="stop")

        with (
            patch.object(service._embed, "create_embedding", new=mock_embed),
            patch.object(service._pinecone, "query_chunks", new=mock_query),
            patch.object(service._tickets, "search_tickets_for_account", new=mock_search),
            patch.object(service._chat, "stream_chat", new=mock_stream),
        ):
            events = [e async for e in service.stream_answer("test query", ACCOUNT_ID)]

        event_text = "".join(events)
        assert "citation" in event_text
        assert "ticket_context" in event_text
        assert "token" in event_text
        assert "done" in event_text
        assert "Here is how" in event_text
        assert "VMware Replication Setup" in event_text

    @pytest.mark.asyncio
    async def test_stream_answer_no_kb_results_still_streams(self):
        service = ChatService()

        async def mock_embed(text):
            return [0.1] * 1024

        async def mock_query(embedding, top_k=5, min_score=0.0):
            return []

        async def mock_search(account_id, query, limit=3):
            return []

        async def mock_stream(messages, temperature=0.3, max_tokens=1024):
            yield ChatChunk(content="I cannot answer", finish_reason="stop")

        with (
            patch.object(service._embed, "create_embedding", new=mock_embed),
            patch.object(service._pinecone, "query_chunks", new=mock_query),
            patch.object(service._tickets, "search_tickets_for_account", new=mock_search),
            patch.object(service._chat, "stream_chat", new=mock_stream),
        ):
            events = [e async for e in service.stream_answer("test", ACCOUNT_ID)]

        event_text = "".join(events)
        assert "done" in event_text

    @pytest.mark.asyncio
    async def test_stream_answer_handles_llm_error(self):
        service = ChatService()

        async def mock_embed(text):
            return [0.1] * 1024

        async def mock_query(embedding, top_k=5, min_score=0.0):
            return []

        async def mock_search(account_id, query, limit=3):
            return []

        async def mock_stream(messages, temperature=0.3, max_tokens=1024):
            raise RuntimeError("LLM timeout")
            yield

        with (
            patch.object(service._embed, "create_embedding", new=mock_embed),
            patch.object(service._pinecone, "query_chunks", new=mock_query),
            patch.object(service._tickets, "search_tickets_for_account", new=mock_search),
            patch.object(service._chat, "stream_chat", new=mock_stream),
        ):
            events = [e async for e in service.stream_answer("test", ACCOUNT_ID)]

        event_text = "".join(events)
        assert "error" in event_text
        assert "trace_id" in event_text


class TestIngestionService:
    def test_extract_title(self):
        from services.ingestion import IngestionService
        content = "# Hello World\n\nSome content here"
        title = IngestionService._extract_title(content)
        assert title == "Hello World"

    def test_extract_title_no_heading(self):
        from services.ingestion import IngestionService
        content = "Just some content without a heading"
        title = IngestionService._extract_title(content)
        assert title == "Untitled"

    def test_split_by_heading(self):
        from services.ingestion import IngestionService
        content = "# Title\n\nIntro text\n\n## Section A\n\nBody A\n\n## Section B\n\nBody B"
        sections = IngestionService._split_by_heading(content)
        assert len(sections) >= 3
        headings = [s[0] for s in sections]
        assert "Title" in headings or "" in headings
        assert "Section A" in headings
        assert "Section B" in headings

    def test_chunk_document_produces_chunks(self):
        from services.ingestion import IngestionService
        service = IngestionService()
        content = "# Test\n\nThis is a test document with enough content to produce at least one chunk."
        chunks = service._chunk_document(content, "Test")
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.title == "Test"
            assert chunk.chunk_index >= 0
            assert len(chunk.content) > 0

    def test_chunk_id_format(self):
        import hashlib
        document_id = "abc123"
        chunk_index = 5
        content = "test content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        chunk_id = f"{document_id}_{chunk_index}_{content_hash}"
        parts = chunk_id.split("_")
        assert parts[0] == document_id
        assert parts[1] == str(chunk_index)
        assert len(parts[2]) == 12
