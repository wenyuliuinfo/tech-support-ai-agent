"""Ingestion CLI entry point — offline pipeline for Knowledge Base documents."""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from services.ingestion import IngestionService

logger = logging.getLogger(__name__)


async def run_ingestion(dry_run: bool = False) -> None:
    service = IngestionService()

    if dry_run:
        logger.info("Dry run mode — computing chunks without upserting")
        kb_path = Path(__file__).parent.parent.parent.parent / "docs" / "knowledge_base"
        for md_file in sorted(kb_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            title = service._extract_title(content)
            chunks = service._chunk_document(content, title)
            print(f"{md_file.name}: {len(chunks)} chunks, title='{title}'")  # noqa: T201
        return

    # Ensure Pinecone index exists before ingesting
    service.ensure_index()

    manifests = await service.ingest_all()
    print(json.dumps(  # noqa: T201
        [
            {
                "source_path": m.source_path,
                "document_id": m.document_id,
                "chunks_upserted": m.chunks_upted,
                "ingestion_version": m.ingestion_version,
            }
            for m in manifests
        ],
        indent=2,
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Base Ingestion Pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute chunks and metadata without upserting to Pinecone",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Ingest a single file instead of the entire KB directory",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.dry_run:
        asyncio.run(run_ingestion(dry_run=True))
    else:
        asyncio.run(run_ingestion(dry_run=False))


if __name__ == "__main__":
    main()
