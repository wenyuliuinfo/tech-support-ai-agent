"""LLM chat and embeddings repositories."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI

from config import get_settings


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatChunk:
    content: str
    finish_reason: str | None = None


class ChatRepository:
    """Chat completion via DeepSeek API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.chat_api_key,
            base_url=settings.chat_base_url,
        )
        self._model = settings.chat_model

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[ChatChunk]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            content = delta.content if delta and delta.content else ""
            finish = chunk.choices[0].finish_reason if chunk.choices else None
            yield ChatChunk(content=content, finish_reason=finish)


class EmbeddingRepository:
    """Embedding generation via OpenAI API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )
        self._model = settings.embedding_model

    async def create_embedding(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [d.embedding for d in response.data]
