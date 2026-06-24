"""Pinecone vector database repository."""

from dataclasses import dataclass
from functools import cached_property
from urllib.parse import urlparse

from pinecone import Index as PineconeIndex
from pinecone import Pinecone as PineconeClient

from config import get_settings


@dataclass(frozen=True)
class ChunkResult:
    chunk_id: str
    document_id: str
    source_path: str
    file_name: str
    chunk_index: int
    content: str
    title: str
    section_heading: str
    score: float


@dataclass(frozen=True)
class ChunkUpsert:
    chunk_id: str
    document_id: str
    source_path: str
    file_name: str
    chunk_index: int
    content: str
    title: str
    section_heading: str
    embedding: list[float]
    ingestion_version: str
    updated_at: str


class PineconeRepository:
    def __init__(self) -> None:
        settings = get_settings()
        control_url = urlparse(settings.pinecone_host_url)
        data_port = control_url.port + 1 if control_url.port else 443
        self._data_host = f"http://{control_url.hostname}:{data_port}"

        self._client = PineconeClient(
            api_key=settings.pinecone_api_key,
            host=settings.pinecone_host_url,
        )
        self._index_name = settings.pinecone_index_name
        self._embedding_dimension = settings.embedding_dimension

    @cached_property
    def _index(self) -> PineconeIndex:
        return self._client.Index(self._index_name, host=self._data_host)

    async def query_chunks(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[ChunkResult]:
        result = self._index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
        )

        chunks: list[ChunkResult] = []
        for match in result.matches:
            if match.score is None or match.score < min_score:
                continue
            meta = match.metadata or {}
            chunks.append(
                ChunkResult(
                    chunk_id=str(meta.get("chunk_id", match.id)),
                    document_id=str(meta.get("document_id", "")),
                    source_path=str(meta.get("source_path", "")),
                    file_name=str(meta.get("file_name", "")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    content=str(meta.get("content", "")),
                    title=str(meta.get("title", "")),
                    section_heading=str(meta.get("section_heading", "")),
                    score=float(match.score),
                )
            )
        return chunks

    async def upsert_chunks(self, chunks: list[ChunkUpsert]) -> None:
        vectors = [
            {
                "id": c.chunk_id,
                "values": c.embedding,
                "metadata": {
                    "document_id": c.document_id,
                    "source_path": c.source_path,
                    "file_name": c.file_name,
                    "chunk_index": c.chunk_index,
                    "chunk_id": c.chunk_id,
                    "content": c.content,
                    "title": c.title,
                    "section_heading": c.section_heading,
                    "ingestion_version": c.ingestion_version,
                    "updated_at": c.updated_at,
                },
            }
            for c in chunks
        ]
        self._index.upsert(vectors=vectors)

    async def delete_by_document_id(self, document_id: str) -> None:
        """Delete all chunks for a document.

        Uses ID-based deletion because serverless Pinecone does not
        support metadata-filtered deletes.
        """
        chunk_ids = await self.document_chunk_ids(document_id)
        if chunk_ids:
            self._index.delete(ids=list(chunk_ids))

    async def document_chunk_ids(self, document_id: str) -> set[str]:
        result = self._index.query(
            vector=[0.0] * self._embedding_dimension,
            top_k=10000,
            filter={"document_id": {"$eq": document_id}},
            include_metadata=False,
        )
        return {match.id for match in result.matches}
