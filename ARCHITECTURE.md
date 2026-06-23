# Tech Support RAG Agent — Technical Architecture Documentation


## 1. Data Model
### 1.1 Vector Database
- Vector Database Decision: Pinecone
- Functionality: Use Pinecone Vector DB to store internal documentation.

#### 1.1.1 Vector DB Metadata
- `document_id`
- `source_path`
- `file_name`
- `chunk_index`
- `chunk_id`
- `content`
- `title`
- `section_heading`
- `ingestion_version`
- `updated_at`

### 1.2 Relational Database
- Relational Database: PostgreSQL
- Functionality: Use PostgreSQL to store account data, historical tickets number.

#### 1.2.1 Users Table (accounts)
  - account_id: Primary key (UUID)
  - email: Email (unique)
  - name: Display name
  - external_id: using external magic link email
  - created_at: Creation timestamp

  Auth approach:
  - External IdP: Auth0/Clerk/Cognito; this table stores `external_id` only, no password field.

#### 1.2.2 Ticket Table (tickets)
  - ticket_number: Primary key
  - account_id: Account number (UUID)
  - subject: Ticket name
  - status: Ticket status
  - created_at: Creation timestamp
  - resolution: Solution provided previously about this ticket

Relationship: One account can have many tickets(one-to-many)


## 2. API Design
- `GET /tickets`
  - Auth: Bearer token required; `account_id` derived from token
  - Response:
    ```
    {"tickets": [{"ticket_number": 1, "account_id": "a1b2c3d4-...", "subject": "Payment issue", "status": "closed", "created_at": "2026-03-19","resolution": "..."}]}
    ```

- `GET /health`
  - Response:
    ```
    {"status": "ok", "timestamp": "..."}
    ```

- `POST /chat`
  - Auth: Bearer token required; `account_id` derived from token
  - Body: 
    ```
    {"query": "How do I enable replication for VMware VMs?"}
    ```
  - Response:
    `text/event-stream` (SSE). Each event is a JSON object on a `data: event` line. 

    Event types:
    - **token** — one chunk of generated answer text - `data: {"type": "token", "content": "To enable "}`
    - **citation** — emitted once per Knowledge Base chunk used to ground the
    answer; may be interleaved with tokens or batched at the end - `data: {"type": "citation", "chunk_id": "doc123_4_a1b2c3", "document_id": "doc123", "source_path": "docs/knowledge_base/vmware-replication.md", "title": "VMware Replication Setup", "section_heading": "Enabling Replication"}`
    - **ticket_context** — emitted if a historical ticket informed the answer (secondary context, never a substitute for a citation) - `data: {"type": "ticket_context", "ticket_number": 4821, "note": "Referenced for account-specific history; not canonical guidance"}`
    - **error** — emitted on LLM/provider failure; terminates the stream - `data: {"type": "error", "message": "LLM provider timeout", "trace_id": "..."}`
    - **done** — terminal event, always sent on a successful or gracefully degraded completion - `data: {"type": "done"}`


## 3. Architecture Diagram
Here we design a RAG system for retrieving internal documents as referenced context.

### 3.1 Data Flow Explanation
#### 3.1.1 Online Query Path (real-time)
1. **Authenticate** - User logs in via the Magic Link authentication (Auth0). On success, the backend issues a session token (JWT) containing `account_id`. The frontend stores this token and attaches it to all subsequent requests (`Authorization: Bearer <token>`).
2. **Load Tickets for Account** - On page load, the Next.js frontend calls `GET /tickets` with the session token. The backend extracts `account_id` from the validated token — it is never read from a query param, form field, or request body. The database returns the ticket list for that account only.
3. **Send Question** - User types a question; Next.js frontend sends `POST /chat` with the session token attached. `account_id` is derived server-side from the token, not from the request body.
4. **Search Past Tickets (relational DB)** - Backend queries the relational DB for tickets belonging to this account that are relevant to the query:
    - Exact match search: ticket `subject` or `resolution` contains keywords from the query;
Database returns matching tickets information.
5. **Retrieve Relevant Documents from Pinecone** - Backend calls the embedding models to convert the user's question into an embedding vector. The vector is sent to Pinecone with a metadata filter to retrieve only relevant document chunks. Pinecone returns the most similar chunks (with metadata: source, chunk text, score).
6. **Build Prompt and call LLM** - Backend constructs a prompt containing:
   - System instructions
   - Retrieved chunks (from Pinecone)
   - The past ticket resolution (if found)
   - User question
  Then it calls the LLM SDK (e.g., `openai.chat.completions.create`).
7. **Stream the Response back to the Frontend** - LLM starts generating tokens and returns them as a stream. Backend streams the tokens as SSE events back to Next.js frontend over the same HTTP connection. Next.js receives the `done` event, stops the streaming and displays the source references.
8. **Completion** - User sees the complete answer with source listed.

#### 3.1.2 Offline Ingestion Path (asynchronous)
##### 3.1.2.1 Document Ingestion
1. **Source Documents** - New documents (PDF, Word, .md file etc.) are originate from `docs/knowledge_base`.
2. **Chunking** - Documents are split into overlapping chunks (e.g., 500 tokens, overlap 50).
3. **Embedding** - Each chunk is passed to the same embedding model to generate a vector.
4. **Upsert to Pinecone** - Vectors are inserted into Pinecone DB along with metadata (file_name, path, chunk_index, content, original_row_index, etc.).

##### 3.1.2.2 Ticket Sync (ETL)
1. **A scheduled job (cron) runs** (e.g., every hour) to pull new/updated tickets from the CRM or ticketing system.
2. **The job inserts/updates ticket records** in the relational database (PostgreSQL) with fields: `ticket_number`, `account_id`, `subject`, `status`, `resolution`, `created_at`.
3. **The main API queries this table** during online requests.


## 4. Third-Party Integrations
### 4.1 OpenAI API
- Purpose: AI conversation features
- Model Decision: GPT-5.4
- Environment variable: OPENAI_API_KEY, OPENAI_BASE_URL
- Limitation: 60 requests per minute

### 4.2 Embedding Model
- Purpose: The embedding model used in business logic
- Embedding Decision: OpenAI text-embedding-3-large


## 5. Technical Decisions
### 5.1 Stack
- **Frontend**: Next.js (client-side, calls backend)
- **Backend**: FastAPI (API route) + Python (Business Logic)
- **Vector DB**: Pinecone
- **Relational DB**: PostgreSQL (store user data and tickets data)

### 5.2 Database Hosting
- **Relational DB**: PostgreSQL (AI has deep understanding, generating accurate data model code)


## 6. Retrieval Policy
The assistant retrieves from two sources:
1. **Knowledge Base Documents**
   Source of truth for product and procedural guidance.
   Documents originate from `docs/knowledge_base` and are embedded into Pinecone.
2. **Ticket Context**
   Historical support tickets for the current `account_id`.
   Tickets are stored in PostgreSQL and may be used to personalize or contextualize the answer.

### 6.1 Retrieval Priority
Knowledge Base Documents are the primary grounding source.
Ticket Context is secondary and must never override current Knowledge Base guidance unless explicitly marked as newer and trusted.

### 6.2 Retrieval Flow
1. Normalize the user query.
2. Retrieve top `k=8` chunks from Pinecone using semantic search.
3. Retrieve up to `k=3` relevant historical tickets for the same `account_id`.
4. Deduplicate chunks by source document and chunk overlap.
5. Optionally re-rank the combined set before prompt construction.
6. Drop low-confidence results below a configured relevance threshold.
7. If no KB chunks pass threshold, answer with a fallback response that states insufficient grounding.

### 6.3 Retrieval Filters
- Knowledge base retrieval is global and not filtered by `account_id`.
- Ticket retrieval is always filtered by `account_id`.
- Future metadata filters may include `product`, `scenario`, and `document_type`.

### 6.4 Citation Rules
Every non-trivial factual answer must cite at least one retrieved Knowledge Base chunk.
Ticket Context may be referenced as supporting context, but not as the sole citation for procedural guidance.


## 7. Prompting and Answer Contract
The backend constructs the final prompt from:
- system instructions
- retrieved Knowledge Base chunks
- optional Ticket Context
- the user query

### 7.1 System Prompt Responsibilities
The system prompt must instruct the model to:
- answer only from provided context when making factual claims
- prefer Knowledge Base Documents over Ticket Context when they conflict
- cite supporting sources
- admit uncertainty when grounding is insufficient
- avoid fabricating steps, settings, or product behavior

### 7.2 Answer Contract
Each streamed answer must satisfy the following:
- Be directly responsive to the user’s question.
- Use retrieved Knowledge Base content as the primary basis for the answer.
- Include citations for factual or procedural claims.
- Clearly separate confirmed guidance from account-specific historical context.
- State when the available context is insufficient.

### 7.3 Fallback Behavior
If retrieval returns no sufficiently relevant Knowledge Base chunks:
- do not generate detailed procedural instructions
- return a short response explaining that no grounded documentation was found
- suggest the closest next step, such as rephrasing the question or contacting support

### 7.4 Conflict Handling
If Ticket Context conflicts with Knowledge Base Documents:
- prefer Knowledge Base Documents
- mention that historical ticket data may be outdated
- do not present the ticket resolution as canonical guidance


## 8. Ingestion Lifecycle
Knowledge Base ingestion is an offline pipeline that transforms repo-managed Markdown documents into searchable vector records.

### 8.1 Source of Truth
The source of truth is the `docs/knowledge_base` directory in the repository.

### 8.2 Lifecycle Stages
1. Detect added, changed, or deleted documents.
2. Parse Markdown into normalized document text and metadata.
3. Split documents into chunks using a deterministic chunking strategy.
4. Generate embeddings for each chunk.
5. Upsert chunk vectors and metadata into Pinecone.
6. Mark deleted or removed documents as tombstoned in the vector store.
7. Record ingestion results, timestamps, and version information.

### 8.3 Chunking Policy
- Default chunk size: 500 tokens
- Default overlap: 50 tokens
- Preserve document title and section headers in chunk metadata
- Keep chunk boundaries stable where possible to reduce embedding churn

### 8.4 Metadata Policy
Each chunk record must include:
- `document_id`
- `source_path`
- `file_name`
- `chunk_index`
- `chunk_id`
- `content`
- `title`
- `section_heading`
- `ingestion_version`
- `updated_at`

### 8.5 Re-indexing Rules
A document is re-embedded when:
- its source file changes
- the chunking strategy changes
- the embedding model changes
- required metadata fields change

### 8.6 Idempotency
Repeated ingestion of the same document version must produce the same chunk IDs and overwrite prior records safely. (e.g. `chunk_id = f"{document_id}_{chunk_index}_{content_hash}"`.)


## 9. Evaluation Plan
The RAG system is evaluated on retrieval quality, answer grounding, and runtime performance.

### 9.1 Evaluation Dataset
Maintain a curated test set of real support questions with:
- expected relevant documents
- expected citations
- expected answer characteristics
- optional known-good ticket context

### 9.2 Retrieval Metrics
Track:
- Recall@k
- Precision@k
- Mean Reciprocal Rank (MRR)
- citation-source match rate

### 9.3 Answer Quality Metrics
Track:
- groundedness
- citation correctness
- answer completeness
- hallucination rate
- refusal correctness when grounding is insufficient

### 9.4 Operational Metrics
Track:
- p50, p95, p99 latency
- embedding latency
- Pinecone query latency
- token usage
- retrieval empty-result rate
- streaming completion rate

### 9.5 Release Gates
Changes to chunking, embeddings, prompting, or retrieval logic must be evaluated against the benchmark set before release.
No change may regress citation correctness or groundedness beyond agreed thresholds.


## 10. Security and Compliance Controls
The system must protect customer data, prevent unauthorized access, and reduce model misuse risks.

### 10.1 Access Control
- Ticket retrieval is always scoped by authenticated `account_id`.
- Knowledge Base retrieval is limited to approved internal support content.
- Administrative ingestion operations require elevated permissions.

### 10.2 PII Handling
- Detect and redact sensitive data before embedding external or customer-derived content.
- Do not embed raw secrets, credentials, or unnecessary personal data.
- Apply retention and deletion policies to ticket-derived data.

### 10.3 Prompt Injection Defense
- Treat retrieved content as untrusted input.
- Strip or ignore instructions inside documents that attempt to override system behavior.
- Never allow retrieved content to change tool use, auth context, or access scope.

### 10.4 Secrets Management
- Store API keys and database credentials in a secret manager.
- Never hardcode secrets in source control.
- Rotate credentials on schedule.

### 10.5 Auditability
- Log request IDs, retrieval source IDs, and model invocation metadata.
- Avoid logging raw sensitive payloads unless explicitly approved and redacted.

### 10.6 Abuse Controls
- Rate limit per account.
- Validate and sanitize all user input.
- Monitor anomalous query patterns and repeated retrieval failures.


## 11. Runtime Topology and Failure Modes
### 11.1 Runtime Topology
The target system consists of:
- Next.js frontend for user interaction
- FastAPI backend for API orchestration
- PostgreSQL for account and ticket data
- Pinecone for Knowledge Base vector search
- LLM provider for answer generation
- offline ingestion worker for indexing `docs/knowledge_base`
- scheduled ETL worker for syncing ticket data

### 11.2 Request Path
1. Frontend sends `POST /chat`.
2. Backend loads relevant Ticket Context from PostgreSQL.
3. Backend retrieves Knowledge Base chunks from Pinecone.
4. Backend builds the prompt and calls the LLM.
5. Backend streams tokens and citations to the frontend over SSE.

### 11.3 Failure Modes
- **Pinecone unavailable**:
Return a degraded response stating that document retrieval is temporarily unavailable.
Do not fabricate an answer from model knowledge alone.

- **PostgreSQL unavailable**:
Proceed without Ticket Context if possible and note that account history could not be loaded.

- **LLM timeout or provider failure**:
Terminate the stream with a structured error event and trace ID.

- **No relevant retrieval results**:
Return an insufficient-grounding response rather than speculative guidance.

- **Ingestion lag**:
Expose document ingestion timestamps so stale knowledge can be detected.

- **Partial downstream slowdown**:
Use timeouts, retries, and circuit breakers on external dependencies.

### 11.4 Observability
Emit tracing spans and metrics for:
- ticket lookup
- vector retrieval
- reranking
- prompt construction
- model latency
- stream duration
- failure type