# Hybrid retrieval strategy

The assistant retrieves from two sources for each chat request: semantic vector search over Knowledge Base Document chunks in Pinecone and account-scoped historical tickets in PostgreSQL. We chose this hybrid approach instead of relying on either source alone because the knowledge base provides current, citable guidance, while ticket history adds useful account-specific context such as past attempts and known environment details.
