# Knowledge base ingestion and versioning

Knowledge Base Documents in `docs/knowledge_base` are the source of truth and must be ingested through a deterministic pipeline that parses Markdown, chunks content predictably, generates embeddings, and upserts versioned chunk records into Pinecone. We are recording this decision because stable chunk IDs and explicit reindexing on document, chunking, or embedding-model changes make the retrieval corpus explainable and safe to evolve without silent drift.
