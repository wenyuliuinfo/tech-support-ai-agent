"""Chat SSE endpoint — streams grounded answers with citations."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.auth import get_account_id_from_request
from services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


chat_service = ChatService()


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    account_id: UUID = Depends(get_account_id_from_request),
):
    return StreamingResponse(
        chat_service.stream_answer(body.query, account_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
