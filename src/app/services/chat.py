"""Chat service: orchestrates retrieval, prompt construction, and streaming."""

import hashlib
import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from repositories.openai_repo import ChatMessage, ChatRepository, EmbeddingRepository
from repositories.pinecone import ChunkResult, PineconeRepository
from repositories.ticket import TicketRecord, TicketRepository

logger = logging.getLogger(__name__)


class ChatService:
    SYSTEM_PROMPT = (
        "You are a technical support assistant. Answer the user's question "
        "using ONLY the provided Knowledge Base context. "
        "If the Knowledge Base does not contain sufficient information to "
        "answer the question confidently, say so clearly and do not guess. "
        "Historical ticket context may inform your understanding but must "
        "never substitute for Knowledge Base guidance. "
        "When citing information, reference the document title and section."
    )

    FALLBACK_PROMPT = (
        "You are a helpful technical support assistant. Answer the user's "
        "question concisely and accurately. No knowledge base or ticket "
        "history is currently available."
    )

    def __init__(self) -> None:
        self._chat = ChatRepository()
        self._embed = EmbeddingRepository()
        self._pinecone = PineconeRepository()
        self._tickets = TicketRepository()

    async def stream_answer(
        self,
        query: str,
        account_id: UUID,
    ) -> AsyncGenerator[str]:
        # Ensure account exists so ticket creation won't fail
        try:
            await self._tickets.ensure_account(account_id)
        except Exception:
            logger.warning("Failed to ensure account, continuing", exc_info=True)

        # Step 1: Generate query embedding
        embedding = await self._embed.create_embedding(query)

        # Step 2: Retrieve Knowledge Base chunks from Pinecone (best-effort)
        kb_chunks: list[ChunkResult] = []
        try:
            kb_chunks = await self._pinecone.query_chunks(embedding, top_k=5)
        except Exception:
            logger.warning("Pinecone query failed, continuing without KB context",
                           exc_info=True)

        # Step 3: Retrieve relevant ticket context from PostgreSQL (best-effort)
        ticket_records: list[TicketRecord] = []
        try:
            ticket_records = await self._tickets.search_tickets_for_account(
                account_id, query, limit=3
            )
        except Exception:
            logger.warning("Ticket search failed, continuing without ticket context",
                           exc_info=True)

        # Step 4: Yield citations
        for chunk in kb_chunks:
            yield self._sse_event("citation", {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "section_heading": chunk.section_heading,
            })

        # Step 5: Yield ticket context
        for ticket in ticket_records:
            yield self._sse_event("ticket_context", {
                "ticket_number": ticket.ticket_number,
                "note": "Referenced for account-specific history; not canonical guidance",
            })

        # Step 6: Build prompt and stream tokens
        messages = self._build_messages(query, kb_chunks, ticket_records)
        full_response: list[str] = []

        try:
            async for chunk in self._chat.stream_chat(messages):
                if chunk.content:
                    full_response.append(chunk.content)
                    yield self._sse_event("token", {"content": chunk.content})
            yield self._sse_event("done", {})

            # After successful stream, persist a ticket
            try:
                await self._tickets.create_ticket(
                    account_id=account_id,
                    subject=query,
                    resolution="".join(full_response),
                )
            except Exception:
                logger.warning("Failed to create ticket", exc_info=True)

        except Exception as e:
            yield self._sse_event("error", {
                "message": str(e),
                "trace_id": hashlib.md5(query.encode()).hexdigest()[:8],
            })

    def _build_messages(
        self,
        query: str,
        kb_chunks: list[ChunkResult],
        ticket_records: list[TicketRecord],
    ) -> list[ChatMessage]:
        has_kb = bool(kb_chunks)
        has_tickets = bool(ticket_records)

        if not has_kb and not has_tickets:
            return [
                ChatMessage(role="system", content=self.FALLBACK_PROMPT),
                ChatMessage(role="user", content=query),
            ]

        context_parts: list[str] = []

        if has_kb:
            context_parts.append("## Knowledge Base Documents")
            for i, chunk in enumerate(kb_chunks, 1):
                context_parts.append(
                    f"[{i}] {chunk.title} — {chunk.section_heading}\n"
                    f"{chunk.content}"
                )

        if has_tickets:
            context_parts.append("## Past Ticket History (Account-Specific)")
            for ticket in ticket_records:
                resolution_text = ticket.resolution or "No resolution recorded"
                context_parts.append(
                    f"- Ticket #{ticket.ticket_number}: {ticket.subject}\n"
                    f"  Resolution: {resolution_text}"
                )

        context_block = "\n\n".join(context_parts) if context_parts else (
            "No relevant knowledge base documents found."
        )

        return [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Context:\n{context_block}\n\nQuestion: {query}",
            ),
        ]

    @staticmethod
    def _sse_event(event_type: str, data: dict) -> str:
        data["type"] = event_type
        return f"data: {json.dumps(data)}\n\n"
