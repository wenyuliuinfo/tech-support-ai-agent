"""Ingestion service: parses KB documents, chunks, embeds, upserts to Pinecone."""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pinecone import Pinecone as PineconeClient

from config import get_settings
from repositories.openai_repo import EmbeddingRepository
from repositories.pinecone import ChunkUpsert, PineconeRepository

logger = logging.getLogger(__name__)

KB_DIR = Path(__file__).parent.parent.parent.parent / "docs" / "knowledge_base"


@dataclass
class ParsedChunk:
    chunk_index: int
    content: str
    title: str
    section_heading: str


@dataclass
class IngestionManifest:
    source_path: str
    document_id: str
    chunks_upted: int
    ingestion_version: str
    updated_at: str


class IngestionService:
    CHUNK_SIZE_CHARS = 2000
    CHUNK_OVERLAP_CHARS = 200

    def __init__(self) -> None:
        self._embed = EmbeddingRepository()
        self._pinecone = PineconeRepository()

    def ensure_index(self) -> None:
        """Create the Pinecone index if it does not already exist."""
        settings = get_settings()
        index_name = settings.pinecone_index_name

        client = PineconeClient(
            api_key=settings.pinecone_api_key,
            host=settings.pinecone_host_url,
        )

        existing_names = [idx.name for idx in client.list_indexes()]
        if index_name in existing_names:
            idx_info = client.describe_index(index_name)
            existing_dim = idx_info.dimension
            if existing_dim == settings.embedding_dimension:
                logger.info("Pinecone index '%s' already exists (dim=%d), skipping creation", index_name, existing_dim)
                return
            logger.warning(
                "Pinecone index '%s' has dimension %d, but config expects %d. Recreating...",
                index_name, existing_dim, settings.embedding_dimension,
            )
            client.delete_index(index_name)

        logger.info("Creating Pinecone index '%s' (dim=%d, metric=cosine)", index_name, settings.embedding_dimension)
        client.create_index(
            name=index_name,
            dimension=settings.embedding_dimension,
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
        )
        logger.info("Pinecone index '%s' created successfully", index_name)

    async def ingest_all(self) -> list[IngestionManifest]:
        manifests: list[IngestionManifest] = []
        kb_path = KB_DIR
        if not kb_path.exists():
            return manifests

        for md_file in sorted(kb_path.glob("*.md")):
            manifest = await self._ingest_file(md_file)
            if manifest:
                manifests.append(manifest)

        return manifests

    async def ingest_file(self, file_path: Path) -> IngestionManifest | None:
        return await self._ingest_file(file_path)

    async def _ingest_file(self, file_path: Path) -> IngestionManifest | None:
        content = file_path.read_text(encoding="utf-8")
        file_name = file_path.name
        source_path = str(file_path.relative_to(KB_DIR.parent))

        document_id = hashlib.sha256(source_path.encode()).hexdigest()[:16]
        ingestion_version = datetime.now(UTC).isoformat()
        title = self._extract_title(content)
        chunks = self._chunk_document(content, title)

        upserts: list[ChunkUpsert] = []
        chunk_texts = [c.content for c in chunks]
        embeddings = await self._embed.create_embeddings(chunk_texts)

        for chunk, embedding in zip(chunks, embeddings, strict=False):
            content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()[:12]
            chunk_id = f"{document_id}_{chunk.chunk_index}_{content_hash}"

            upserts.append(
                ChunkUpsert(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    source_path=source_path,
                    file_name=file_name,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    title=chunk.title,
                    section_heading=chunk.section_heading,
                    embedding=embedding,
                    ingestion_version=ingestion_version,
                    updated_at=ingestion_version,
                )
            )

        await self._pinecone.delete_by_document_id(document_id)
        if upserts:
            await self._pinecone.upsert_chunks(upserts)

        return IngestionManifest(
            source_path=source_path,
            document_id=document_id,
            chunks_upted=len(upserts),
            ingestion_version=ingestion_version,
            updated_at=ingestion_version,
        )

    def _chunk_document(self, content: str, title: str) -> list[ParsedChunk]:
        sections = self._split_by_heading(content)
        chunks: list[ParsedChunk] = []
        chunk_index = 0

        for section_heading, section_text in sections:
            pos = 0
            while pos < len(section_text):
                end = min(pos + self.CHUNK_SIZE_CHARS, len(section_text))
                chunk_text = section_text[pos:end]

                chunks.append(
                    ParsedChunk(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        title=title,
                        section_heading=section_heading,
                    )
                )
                chunk_index += 1
                pos += self.CHUNK_SIZE_CHARS - self.CHUNK_OVERLAP_CHARS

        return chunks

    @staticmethod
    def _extract_title(content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return "Untitled"

    @staticmethod
    def _split_by_heading(content: str) -> list[tuple[str, str]]:
        heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(content))

        if not matches:
            return [("", content)]

        sections: list[tuple[str, str]] = []
        for i, match in enumerate(matches):
            heading = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            sections.append((heading, content[start:end].strip()))

        first_start = matches[0].start()
        if first_start > 0:
            pre_content = content[:first_start].strip()
            if pre_content:
                sections.insert(0, ("", pre_content))

        return sections
