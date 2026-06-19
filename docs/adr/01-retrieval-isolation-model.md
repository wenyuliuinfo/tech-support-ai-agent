# Retrieval isolation model

Knowledge Base Documents under `docs/knowledge_base` are global support content and are retrieved without `account_id` scoping, while Ticket Context in PostgreSQL is always scoped to the authenticated `account_id`. We chose this split because knowledge-base guidance is the canonical source for product and operational instructions, while tickets are customer-specific historical context that should personalize answers without becoming the source of truth.
