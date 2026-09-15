"""Ingestion pipeline: parse KB documents, chunk, embed, and upsert to Pinecone."""

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pinecone import Pinecone as PineconeClient

from config import get_settings
from repositories.openai_repo import EmbeddingRepository
from repositories.pinecone import ChunkUpsert, PineconeRepository

from .parsers.markdown import extract_title, split_by_heading
from .parsers.models import ParsedSection

logger = logging.getLogger(__name__)
KB_DIR = Path(__file__).parent.parent.parent.parent.parent / "docs" / "knowledge_base"
SUPPORTED_EXTENSIONS = {".md": "md", ".pdf": "pdf", ".docx": "docx"}
@dataclass
class ParsedChunk:
    chunk_index: int
    content: str
    title: str
    section_heading: str
    document_type: str = "md"
    page_number: int | None = None

@dataclass
class IngestionManifest:
    source_path: str
    document_id: str
    chunks_upted: int
    ingestion_version: str
    updated_at: str


class IngestionService:
    CHUNK_SIZE_CHARS = 500
    CHUNK_OVERLAP_CHARS = 50
    CHUNK_SIZE_TOKENS = CHUNK_SIZE_CHARS
    CHUNK_OVERLAP_TOKENS = CHUNK_OVERLAP_CHARS
    MIN_EXTRACTED_TEXT_LENGTH = 10

    def __init__(self) -> None:
        self._embed = EmbeddingRepository()
        self._pinecone = PineconeRepository()
        self._storage = None

    def ensure_index(self) -> None:
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
                logger.info(
                    "Pinecone index '%s' already exists (dim=%d), skipping creation",
                    index_name,
                    existing_dim,
                )
                return
            logger.warning(
                "Pinecone index '%s' has dimension %d, but config expects %d. Recreating...",
                index_name,
                existing_dim,
                settings.embedding_dimension,
            )
            client.delete_index(index_name)

        logger.info(
            "Creating Pinecone index '%s' (dim=%d, metric=cosine)",
            index_name,
            settings.embedding_dimension,
        )
        client.create_index(
            name=index_name,
            dimension=settings.embedding_dimension,
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
        )
        logger.info("Pinecone index '%s' created successfully", index_name)

    async def ingest_all(self) -> list[IngestionManifest]:
        manifests: list[IngestionManifest] = []
        storage = self._get_storage()
        objects = await storage.list("knowledge-base/")

        for obj in objects:
            if self._document_type(Path(obj.key).name) is None:
                logger.warning("Skipping unsupported MinIO object: %s", obj.key)
                continue
            manifest = await self._ingest_storage_object(obj)
            if manifest:
                manifests.append(manifest)

        return manifests

    async def ingest_file(self, file_path: Path) -> IngestionManifest | None:
        data = file_path.read_bytes()
        try:
            source_path = str(file_path.relative_to(KB_DIR.parent))
        except ValueError:
            source_path = file_path.name

        return await self._ingest_bytes(
            file_name=file_path.name,
            source_path=source_path,
            data=data,
        )

    async def _ingest_storage_object(self, obj) -> IngestionManifest | None:
        file_name = Path(obj.key).name
        source_path = f"knowledge_base/{file_name}"
        parts = obj.key.strip("/").split("/")

        if len(parts) >= 4 and parts[0] == "knowledge-base":
            document_id = parts[1]
            ingestion_version = parts[2]
        else:
            document_id = self._document_id(source_path)
            ingestion_version = datetime.now(UTC).isoformat()

        data = await self._get_storage().get(obj.key)
        return await self._ingest_bytes(
            file_name=file_name,
            source_path=source_path,
            data=data,
            storage_key=obj.key,
            document_id=document_id,
            ingestion_version=ingestion_version,
        )

    async def _ingest_bytes(
        self,
        file_name: str,
        source_path: str,
        data: bytes,
        storage_key: str | None = None,
        document_id: str | None = None,
        ingestion_version: str | None = None,
    ) -> IngestionManifest | None:
        document_type = self._document_type(file_name)
        if document_type is None:
            logger.warning("Skipping unsupported file: %s", file_name)
            return None

        title, sections = self._parse_document(file_name, data, document_type)
        extracted_text = "\n".join(section.text for section in sections).strip()
        if len(extracted_text) < self.MIN_EXTRACTED_TEXT_LENGTH:
            logger.warning(
                "Skipping %s: extracted text is empty or too short (%d chars)",
                file_name,
                len(extracted_text),
            )
            return None

        chunks = self._chunk_sections(sections, title, document_type)
        if not chunks:
            logger.warning("Skipping %s: no non-empty chunks produced", file_name)
            return None

        document_id = document_id or self._document_id(source_path)
        ingestion_version = ingestion_version or datetime.now(UTC).isoformat()
        settings = get_settings()
        storage_bucket = settings.minio_bucket_name
        storage_key = storage_key or f"knowledge-base/{document_id}/{ingestion_version}/{file_name}"

        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await self._embed.create_embeddings(chunk_texts)

        upserts: list[ChunkUpsert] = []
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()[:12]
            chunk_id = f"{document_id}_{chunk.chunk_index}_{content_hash}"
            upserts.append(
                ChunkUpsert(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    source_path=source_path,
                    storage_key=storage_key,
                    storage_bucket=storage_bucket,
                    file_name=file_name,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    title=chunk.title,
                    section_heading=chunk.section_heading,
                    document_type=chunk.document_type,
                    page_number=chunk.page_number,
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

    def _parse_document(
        self,
        file_name: str,
        data: bytes,
        document_type: str,
    ) -> tuple[str, list[ParsedSection]]:
        if document_type == "md":
            content = data.decode("utf-8")
            return extract_title(content), split_by_heading(content)

        if document_type == "pdf":
            from .parsers.pdf import parse_pdf
            return self._fallback_title(file_name), parse_pdf(data)

        if document_type == "docx":
            from .parsers.docx import parse_docx
            sections = parse_docx(data)
            title = next(
                (section.heading for section in sections if section.heading),
                self._fallback_title(file_name),
            )
            return title, sections

        raise ValueError(f"Unsupported document type: {document_type}")

    def _chunk_sections(
        self,
        sections: list[ParsedSection],
        title: str,
        document_type: str,
    ) -> list[ParsedChunk]:
        chunks: list[ParsedChunk] = []
        chunk_index = 0

        for section in sections:
            if not section.text.strip():
                continue
            pos = 0
            while pos < len(section.text):
                end = min(pos + self.CHUNK_SIZE_CHARS, len(section.text))
                chunk_text = section.text[pos:end]
                chunks.append(
                    ParsedChunk(
                        chunk_index=chunk_index,
                        content=chunk_text,
                        title=title,
                        section_heading=section.heading or "",
                        document_type=document_type,
                        page_number=section.page_number,
                    )
                )
                chunk_index += 1
                pos += self.CHUNK_SIZE_CHARS - self.CHUNK_OVERLAP_CHARS

        return chunks

    def _chunk_document(self, content: str, title: str) -> list[ParsedChunk]:
        sections = split_by_heading(content)
        return self._chunk_sections(sections, title, "md")

    def _get_storage(self):
        if self._storage is None:
            from repositories.storage import StorageRepository
            self._storage = StorageRepository()
        return self._storage

    @staticmethod
    def _document_type(file_name: str) -> str | None:
        return SUPPORTED_EXTENSIONS.get(Path(file_name).suffix.lower())

    @staticmethod
    def _document_id(source_path: str) -> str:
        return hashlib.sha256(source_path.encode()).hexdigest()[:16]

    @staticmethod
    def _fallback_title(file_name: str) -> str:
        return Path(file_name).stem.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _extract_title(content: str) -> str:
        return extract_title(content)

    @staticmethod
    def _split_by_heading(content: str) -> list[tuple[str, str]]:
        return [(section.heading or "", section.text) for section in split_by_heading(content)]
