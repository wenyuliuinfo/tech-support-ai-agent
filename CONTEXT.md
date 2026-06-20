# Tech Support AI Agent

This context defines the core business language for the tech support RAG system.
It exists to keep product, retrieval, and support concepts consistent across architecture, APIs, and implementation.

## Language

**Account**:
The customer account that owns support history and is used to scope ticket retrieval.
_Avoid_: User, customer, tenant, username

**End User**:
The person interacting with the support assistant through the frontend.
_Avoid_: Account, customer account

**Ticket**:
A support case associated with an `Account`, containing issue subject, status, and historical resolution data.
_Avoid_: Case, incident, request

**Knowledge Base Document**:
A curated support or product document stored in `docs/knowledge_base` and used as a grounding source for retrieval.
_Avoid_: Ticket, attachment, customer document

**Chunk**:
A retrieval unit produced by splitting a `Knowledge Base Document` into smaller segments for embedding and search.
_Avoid_: Snippet, fragment, passage

**Citation**:
A reference in an answer that points back to one or more retrieved `Chunks` and their source `Knowledge Base Document`.
_Avoid_: Link, source text

**Retrieved Context**:
The set of `Chunks` and optional `Ticket` information selected for grounding a single answer.
_Avoid_: Memory, history, prompt

**Ticket Context**:
Historical support information retrieved from past `Tickets` for an `Account` and used as secondary context during answer generation.
_Avoid_: Knowledge base, citation

**Answer**:
The assistant’s grounded response to an `End User` query, generated from retrieved context.
_Avoid_: Completion, output

**Ingestion**:
The offline process that reads `Knowledge Base Documents`, chunks them, embeds them, and writes them into the vector store.
_Avoid_: Retrieval, indexing job

**Embedding**:
The vector representation of a query or `Chunk` used for semantic search.
_Avoid_: Feature, tokenization

**Retrieval**:
The process of selecting relevant `Knowledge Base Documents` and optional `Ticket Context` for a user query.
_Avoid_: Generation, ingestion

**Grounding**:
The requirement that an `Answer` be supported by retrieved knowledge base content rather than unsupported model knowledge.
_Avoid_: Hallucination prevention, prompting