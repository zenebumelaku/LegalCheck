# LegalCheck Ethiopia

LegalCheck Ethiopia provides evidence-grounded legal research and answers
using a React frontend and FastAPI backend. The backend includes authentication,
legal-source management, document ingestion, retrieval, and optional answer
caching.

## Requirements

- Python 3.11 or newer
- PostgreSQL with pgvector for the application database and semantic retrieval
- Redis for request rate limiting and optional answer caching
- Node.js/npm only when building or running the React frontend

The API and database are required. Redis is used by rate-limited operations
and optional answer caching; rate limiting fails closed if Redis is unavailable.
Embeddings and LLM generation are optional, but answering a legal question
requires eligible indexed sources and a configured LLM provider.

## Set up the backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Update `DATABASE_URL` in `.env` with the connection URL for your PostgreSQL
database. Start PostgreSQL separately before running migrations or calling the
readiness endpoint. For example, with a locally installed Homebrew service,
start the installed PostgreSQL service with `brew services start postgresql@16`
(use the service name for your installed version).
Create the database if needed with `createdb legalcheck`. The default sample
URL is `postgresql+psycopg://username:password@localhost:5432/legalcheck`;
replace the placeholder credentials with a local database role and password.

`CORS_ORIGINS` is a JSON array of allowed origins, for example
`["http://localhost:3000"]`. Do not commit `.env` or put real credentials in
`.env.example`.

The database URL must point to PostgreSQL. The legal retrieval migrations use
pgvector; make sure the extension is available and the migration role has the
required permissions. Configure database, Redis, LLM, and embedding credentials
only in an ignored local `.env` file or a deployment secret manager. The
application does not read `SECRET_KEY`; do not rely on it as an application
security setting.

Start Redis separately, for example with `redis-server`. Set `REDIS_URL` to
that service. Do not reuse development database or Redis URLs in production.

## Run the application

With the virtual environment activated and the shell in `backend/`:

```bash
uvicorn app.main:app --reload
```

The interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

For the frontend, configure `VITE_API_BASE_URL` in your local
`frontend/.env`, then run:

```bash
cd frontend
npm ci
npm run dev
```

The frontend does not contain provider credentials. Keep
`VITE_ENABLE_DEMO_FALLBACK=false` except when intentionally testing the visibly
labeled synthetic demo behavior.

## Password reset email

Password reset is available only when the backend email provider is configured.
The default `PASSWORD_RESET_EMAIL_PROVIDER=disabled` makes the request endpoint
return an explicit configuration error. To enable Resend, set
`PASSWORD_RESET_EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and
`PASSWORD_RESET_FROM_EMAIL` in the backend's ignored `.env` file. The sender
address must be authorized in the Resend account. Set
`PASSWORD_RESET_FRONTEND_URL` to the frontend origin; production must use
HTTPS. `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` defaults to 30.

The request API uses the same generic response for registered and unknown email
addresses. Reset tokens are random, one-time values; only their SHA-256 hashes
are stored, and the emailed link carries its token in the URL fragment so it is
not sent to the web server in the HTTP request. Successful password changes
consume the token and revoke existing login sessions. Resend failures are
logged without the email address, token, or API key, while the public request
response remains generic to avoid account enumeration. No email is delivered
until valid Resend credentials and a sender are configured. Never put Resend
credentials in frontend environment variables or source control.

## Environment and providers

`backend/.env.example` lists supported backend settings; copy it to `.env` and
replace local connection placeholders. `DATABASE_URL` and `REDIS_URL` are
service connection strings. `CORS_ORIGINS` is a JSON array of exact frontend
origins.

LLM generation is disabled by default. To enable it, configure
`LLM_PROVIDER=openai_compatible`, `LLM_PROVIDER=ollama`, or
`LLM_PROVIDER=gemini`, plus the provider's `LLM_API_URL` (where applicable),
`LLM_MODEL_NAME`, and `LLM_API_KEY` as appropriate. Gemini uses Google's
Generative Language API over HTTPS and the API key is sent only in the
`x-goog-api-key` request header. For legal-Q&A-only generation, set
`LLM_PROVIDER=disabled` and `LEGAL_QA_LLM_PROVIDER=gemini` (or another supported
provider); this isolates legal Q&A from other application behavior. The Q&A
override uses the configured model, version, URL, and key settings, and is
included in cache keys.

Gemini retries one network or 5xx failure; rate limits and
unavailable models are reported explicitly rather than retried indefinitely.
Update `LLM_MODEL_NAME` when a configured Gemini model is retired.

Ollama requires a separately installed/running server and available model.
Remote endpoints must follow the application's HTTPS rules; unauthenticated
HTTP is limited to loopback development endpoints. If the provider is disabled,
missing, rate-limited, or unavailable, legal Q&A returns a clear error; it
never substitutes a sample answer. No paid provider is bundled or required for
startup.

Embeddings are independently optional. `EMBEDDING_PROVIDER=disabled` omits
vector retrieval; exact-article and BM25 keyword retrieval still work.
Configure the supported OpenAI-compatible
embedding endpoint, or explicitly install and provision the optional local
Sentence Transformers model as described in
[Legal retrieval and embeddings](#legal-retrieval-and-embeddings). The local
model is not downloaded during ordinary startup or tests. Embedding model
versions must remain compatible with the database's 384-dimensional vectors;
re-index when intentionally changing the model version.

## Answer cache configuration

The answer cache uses `REDIS_URL` and stores legal Q&A responses under a
separate key namespace.
`LEGAL_QA_CACHE_TTL_SECONDS` defaults to 3600 seconds; setting it to `0`
disables answer caching without disabling Redis-backed rate limiting.
`LEGAL_QA_CACHE_VERSION` defaults to `v1`; increment it to make old answer keys
unreachable after answer-logic or configuration changes not already included
in the key. Retrieval mode, RRF offset, candidate/result cutoffs,
reranker model path/version, and embedding configuration are also part of the
key. Legal-source/provision/index changes update the knowledge-base fingerprint
automatically. Old versioned entries expire by TTL and are not physically
deleted at invalidation time.

Redis cache read/write failures are fail-open for Q&A: the request continues to
retrieval and generation and does not return a fabricated answer. This is
separate from rate limiting, which fails closed when Redis is unavailable.

## Deployment configuration

The repository's existing [`render.yaml`](./render.yaml) describes a Render
web API, PostgreSQL, and Redis. It is a hosting blueprint, not a deployment
verification: it has not been deployed or tested against a Render account. It
runs migrations in the API build command and starts the API service.
The frontend is not deployed by that blueprint and needs a separate static
frontend deployment with `VITE_API_BASE_URL` pointing to the API.

The blueprint sets LLM and embedding providers to `disabled`. API startup can
succeed in that state, but answer generation returns an explicit unavailable-
provider error. Configure supported providers using the hosting platform's
secret/environment settings before relying on AI answers. Confirm PostgreSQL
pgvector availability and migration permissions for the selected database plan.

The blueprint configures local private-file storage. [Render persistent
disks](https://render.com/docs/disks) attach to a specific service. Use an
approved private object store for uploaded files in a multi-instance production
deployment; do not treat local storage as production-ready for shared use.

This repository intentionally has no Docker Compose setup. For local
development, start PostgreSQL with pgvector and Redis using the host's supported
installation, then follow the migration and API commands above. No
credentials or local provider secrets belong in checked-in example files.

## Database migrations

With PostgreSQL running and `DATABASE_URL` set in `.env`, from `backend/`:

```bash
alembic upgrade head
```

Apply migrations before starting the API so the full application schema,
including authentication sessions, password-reset tokens, and the
case-insensitive email index, exists.

Create future migrations after changing the models with:

```bash
alembic revision --autogenerate -m "describe schema change"
```

## Health endpoints

- `GET /api/v1/health` reports that the API process is responding.
- `GET /api/v1/health/ready` runs `SELECT 1` against PostgreSQL and returns
  HTTP 503 if `DATABASE_URL` is missing or the database cannot be reached.

## Run tests

From `backend/` with the virtual environment activated:

```bash
pytest
```

## Authentication

Authentication uses revocable bearer tokens. A successful login returns a
random token; the database stores only its SHA-256 hash and expiry. Send it on
protected requests as `Authorization: Bearer <access_token>`. Tokens expire
after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60; maximum 24 hours), and
`POST /api/v1/auth/logout` revokes the presented token. Use HTTPS in
deployments so bearer tokens are protected in transit.

Example requests after starting the API:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Example User","email":"user@example.com","password":"a-long-password"}'

curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"a-long-password"}'

curl http://127.0.0.1:8000/api/v1/auth/me \
  -H 'Authorization: Bearer <access_token>'
```

Available auth endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/password-reset-request`

Passwords are hashed with Argon2id. Registration accepts a name, email, and
password (minimum 12 characters); role and active status are assigned
server-side. Email addresses are trimmed and normalized to lowercase and have
a case-insensitive unique database index. The reset-request endpoint only
returns a generic response: email delivery and reset tokens are not implemented
until an email provider is configured. Redis-backed rate limits apply to login,
registration, and password-reset requests. Configure
`RATE_LIMIT_LOGIN_PER_MINUTE` and `RATE_LIMIT_AUTH_PER_MINUTE` in
`backend/.env`; these endpoints return 503 when Redis is unavailable rather
than bypassing the limit.

## Private document storage

Configure `MAX_UPLOAD_SIZE_MB` (default 10; maximum 100),
`MAX_DOCX_UNCOMPRESSED_SIZE_MB` (default 50; maximum 500),
`PRIVATE_STORAGE_PATH` (default `var/private-documents`) and `OCR_ENABLED`
(default `false`) in `backend/.env`. Local storage is created outside the
application's public web root with restricted directory/file permissions.
Keep the storage directory on a private, access-controlled volume, exclude it
from web-server static roots and backups that are not approved for contracts,
and ensure it has sufficient disk capacity.

`PrivateFileStorage` is the storage boundary for private file persistence.
Local development uses `LocalPrivateFileStorage`; future object-storage
backends should implement that interface using private buckets and server-side
access controls. Original filenames are metadata only; generated keys identify
stored objects. The ordinary document metadata endpoints never return storage
keys or file contents.

Uploads accept PDF and DOCX only. When `OCR_ENABLED=true` and the local
`tesseract` executable is installed, low-text PDF pages are rasterized and
processed with the English (`eng`) Tesseract language data. OCR is bounded to
100 pages per document and 20 seconds per page. Missing Tesseract, timeouts,
and failures are reported as processing warnings; OCR text may be inaccurate
and must be checked against the original. OCR is off by default and is not
bundled with the Python application. DOCX page numbers are not available from
the document structure, so extraction includes paragraph references without
inventing page numbers. Delete removes the private file and soft-deletes
metadata to preserve database references. If physical cleanup fails, the API
reports that cleanup is pending while leaving the metadata soft-deleted.

An authenticated legal-question endpoint provides preliminary,
evidence-grounded AI answers when eligible legal sources and an LLM provider
are available. It abstains when evidence is absent or uncertain; it does not make legal judgments.
Legal-source status is initialized to `unknown`; records are not considered
current unless their status and verification are established explicitly.

## Legal source registry

The public read endpoints are:

- `GET /api/v1/legal-sources` — paginated registry, with optional `q`, `title`,
  `law_number`, `article_number`, `language`, `source_type`, and `legal_status`
  filters.
- `GET /api/v1/legal-sources/search` — the same filters with an explicit search
  route.
- `GET /api/v1/legal-sources/{source_id}` — source provenance and review
  metadata.
- `GET /api/v1/legal-sources/{source_id}/provisions` — paginated provisions,
  filterable by article, sub-article, and language.

Ingestion and review are restricted to users with the server-assigned `admin`
role. Import a source using `POST /api/v1/legal-sources/ingest` as
`multipart/form-data`, with:

- `file`: the source PDF (maximum `MAX_UPLOAD_SIZE_MB`).
- `metadata_json`: JSON containing `title`, `law_number`, `source_type`,
  `jurisdiction`, `language`, `version_label`, `original_source_url`, and
  optional publication/effective/end dates.
- `provisions_json`: a JSON array of curated provisions. Each has an
  `article_number`, `text`, and optional `sub_article_reference`,
  `section_title`, `page_number`, and `language`.

The service validates PDF signature markers and MIME/extension agreement,
computes a SHA-256 checksum, keeps the original PDF in private storage, and
creates a new version record without replacing earlier records. An identical
checksum or an already-used law-number/version-label pair is rejected. The
initial verification status is `pending` and legal status is `unknown`.
Provision references must be reviewed against the uploaded document; the
service does not infer article boundaries or legal conclusions from raw PDF
text.

A different administrator must review the ingestion using
`POST /api/v1/legal-sources/{source_id}/verify` with a `decision` of `verified`
or `rejected`, a `legal_status` (`unknown`, `current`, `amended`, `repealed`,
or `superseded`), and substantive `verification_notes`. The reviewer must
confirm the source against an authoritative publication, validate the
document/version and provisions, and assess amendments and applicability.
Only a source that is verified and explicitly classified `current` is marked
eligible for production findings; `unknown` remains ineligible. Rejected
sources are excluded from public registry results. Status decisions are not
automatically changed when a newer version is ingested.

If the source text is verified but effective dates or current applicability
need a separate review, an administrator other than the ingester can record a
later decision with
`POST /api/v1/legal-sources/{source_id}/applicability-review`. The request
accepts `legal_status`, optional `effective_date` and `end_date`, and
substantive `verification_notes`. Each applicability review is retained with
its reviewer and timestamp; it does not overwrite the original provenance
verification. A `current` decision requires an effective date. Do not select
`current` merely because the source PDF states its commencement date; review
amendments, repeal, and applicability separately. Any change updates the
knowledge-base version used by legal-answer caching.

For example, after a separate review establishes the commencement date but not
amendment status, record the date while keeping status unknown:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/legal-sources/<source-id>/applicability-review" \
  -H "Authorization: Bearer <reviewer-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"legal_status":"unknown","effective_date":"<verified-date>","verification_notes":"<cite the commencement clause and note unresolved amendments/current applicability>"}'
```

To import an actual Ethiopian employment instrument, first obtain the
publication from an authoritative Ethiopian legal publisher or government
source, independently confirm its citation, dates, amendments/repeal status,
language, and the applicability period, then have one administrator ingest
the original PDF and curated provision references. A second administrator
must complete the review and record the evidence in notes. Use a distinct
`version_label` and upload the changed original for each new version; never
edit an existing version in place. No Labour Proclamation No. 1156/2019 PDF
or article text is bundled or seeded by this project, and its current
applicability has not been asserted by this implementation.

Example import request after the source and provisions have been checked by
the importer (replace placeholders only with verified source data):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/legal-sources/ingest \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F 'metadata_json={"title":"<verified title>","law_number":"<verified citation>","source_type":"proclamation","jurisdiction":"<verified jurisdiction>","language":"<verified language>","version_label":"<unique version label>","original_source_url":"<authoritative HTTP(S) URL>"}' \
  -F 'provisions_json=[{"article_number":"<article reference>","sub_article_reference":"<optional sub-article>","section_title":"<verified heading>","text":"<transcribed provision>","page_number":1}]' \
  -F 'file=@/secure/path/to/source.pdf;type=application/pdf'

curl -X POST "http://127.0.0.1:8000/api/v1/legal-sources/<source-id>/verify" \
  -H "Authorization: Bearer $SECOND_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision":"verified","legal_status":"unknown","verification_notes":"<describe authoritative verification and applicability evidence>"}'
```

# LegalCheck

# LegalCheck

## Legal retrieval and embeddings

The single legal-evidence retriever retains exact-article lookup and supports
two lexical/vector strategies. The default `LEGAL_RETRIEVAL_MODE=hybrid`
combines application-side BM25 and the existing pgvector semantic search with
reciprocal rank fusion. `LEGAL_RETRIEVAL_MODE=baseline` retains the earlier
keyword-ranking path for comparison. Exact article matches remain part of the
rank fusion in both modes. Candidate rows are keyed by provision ID, so
overlapping chunks do not produce duplicate provisions; the selected passage
retains provision/article, source/version, page, and URL metadata.

```mermaid
flowchart LR
  Q[Question] --> X[Exact article lookup]
  Q --> B[BM25 lexical retrieval]
  Q --> V[Vector retrieval]
  X --> F[RRF fusion and provision deduplication]
  B --> F
  V --> F
  F --> C[Top 20 candidates]
  C --> R[Optional local cross-encoder]
  R --> K[Top 5 evidence passages]
  K --> L[Answer generation]
  Q --> H{Redis answer cache}
  H -->|hit| A[Cached answer and citations]
  H -->|miss| X
```

BM25 ranks curated provision text using query-term frequency, inverse document
frequency across eligible provisions, and document-length normalization.
Vector search reuses the existing 384-dimensional provision chunks and
configured embedding provider. RRF adds `1 / (offset + rank)` from each
retrieval list (with a deliberate higher weight for exact-article matches);
`LEGAL_RETRIEVAL_RRF_OFFSET` defaults to 60. The final candidate list is
deduplicated by provision before reranking.

Cross-encoder reranking is optional and disabled by default. Set
`LEGAL_RERANKER_ENABLED=true`, `LEGAL_RERANKER_MODEL_PATH` to an existing local
Sentence Transformers cross-encoder directory, and
`LEGAL_RERANKER_MODEL_VERSION` to its revision label. The cross-encoder scores
up to `LEGAL_RETRIEVAL_CANDIDATE_K` (default 20) fused candidates and answer
generation receives up to `LEGAL_QA_TOP_K` (default 5) eligible passages.
There is no model download during application startup; missing model files,
load errors, and inference errors are logged and fall back to fused order.
The same optional `sentence-transformers` package is used for local embeddings
and reranking; install it only when enabling one of those local models, and
provision model files explicitly.

The answer service checks Redis before retrieval, embedding, or LLM generation.
A hit returns the cached answer and source citations. A miss retrieves and
validates evidence, calls the configured LLM, and caches only a supported
answer plus its citations for the configured TTL. Redis errors fail open and
continue through retrieval/generation. The key includes the question/context,
knowledge-base fingerprint, and retrieval/embedding/reranker/LLM configuration,
so changing those settings or indexed legal content cannot reuse an
inappropriately stale answer. TTL expiry and key versioning remain unchanged.

PostgreSQL `pgvector` is required for vector search. Apply the latest Alembic
migration after installing PostgreSQL with pgvector available:

```bash
cd backend
alembic upgrade head
```

Use pgvector extension version 0.5 or newer for the HNSW index. The migration
runs `CREATE EXTENSION IF NOT EXISTS vector`. The database role
must be allowed to create the extension; on managed PostgreSQL where that is
not permitted, have the database administrator enable pgvector first, then
apply the migration. The migration adds a vector column sized for 384 values,
a cosine HNSW index, and a GIN full-text index. Existing legal sources and
provisions are unchanged; embeddings are generated only for verified sources.

Embedding generation is disabled by default, so ordinary tests need no paid
provider account. Configure an OpenAI-compatible embedding endpoint in
`backend/.env` when you are ready to index real, verified source provisions:

```dotenv
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_URL=https://your-provider.example/v1
EMBEDDING_API_KEY= # optional for a private local endpoint; otherwise set privately
EMBEDDING_MODEL_NAME=your-384-dimension-embedding-model
EMBEDDING_MODEL_VERSION=provider-model-revision
```

The endpoint must implement `POST {EMBEDDING_API_URL}/embeddings`, accept
`model`, `input`, and `dimensions: 384`, and return an OpenAI-compatible
`data` list with indexed embedding vectors. Provider credentials must be kept
in `.env` or a secret manager and must not be committed. Embedding model name
and version are recorded on every chunk; changing either creates a separate
index rather than mixing incompatible vectors. The database vector dimension
is fixed at 384; changing it requires a planned schema migration and a
matching provider. Indexing sends provision text to the configured embedding
endpoint, so configure only a provider approved to process the source material.
Remote embedding and analysis endpoints must use HTTPS; unauthenticated HTTP
is accepted only for loopback development endpoints such as `localhost`.

For fully local embeddings, the optional `sentence_transformers` provider
uses `all-MiniLM-L6-v2`, which matches the database's 384-dimensional vectors.
It is disabled by default and does not download model files during application
startup, tests, or indexing. Install the optional package and explicitly
provision the model directory before enabling it:

```bash
cd backend
python -m pip install sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('/absolute/path/all-MiniLM-L6-v2')"
```

Then configure `EMBEDDING_PROVIDER=sentence_transformers` and
`EMBEDDING_LOCAL_MODEL_PATH=/absolute/path/all-MiniLM-L6-v2`. The provider loads
only that existing directory (`local_files_only=True`) and fails clearly if
the package/model is missing or it does not produce 384 dimensions. The
existing `openai_compatible` provider remains available and unchanged.
When replacing model files at the same path, update
`EMBEDDING_MODEL_VERSION` and re-index so the new vectors are not mixed with
the previous model revision.

Once a source has passed the registry's independent verification workflow,
generate its embeddings with:

```bash
cd backend
python -m app.scripts.generate_legal_embeddings
python -m app.scripts.generate_legal_embeddings --source-id <verified-source-uuid>
```

The script indexes only sources with `verification_status=verified`. It
preserves source version, article, sub-article, heading, and page references in
chunks. Each result identifies its source and reports `indexed` or `unchanged`.
If a provider fails for one source, that source's pending chunk writes are
rolled back and the command exits with the source ID and failure type; other
sources already completed in the same command remain committed. Re-running an
unchanged model version does not re-embed completed chunks. If source text,
article metadata, version, or page metadata no longer matches an existing
chunk, indexing refuses to overwrite the previous indexed record; ingest a
distinct legal-source version or choose a new embedding version.

An ingested source remains pending until a different admin reviews it. A
source is eligible for authoritative findings only when verified, explicitly
marked current, supported by retained file provenance, and supplied with an
effective date. An unknown effective date or legal status remains ineligible
or applicability-uncertain; neither is inferred from PDF contents. Rejected,
pending, unknown-status, and otherwise ineligible records are not promoted to
authoritative answers. Ingestion stores the submitted metadata and provisions;
it does not establish that the submitted article boundaries or legal status
are correct.

No verified Ethiopian legal corpus is bundled with this repository. An empty
registry, synthetic test fixture, or successful integration test is not
evidence that real Ethiopian law has been indexed or verified. Populate
production sources only through the existing provenance and independent-review
workflow.

Provisions remain intact when they fit the configured chunk window;
long provisions are split on paragraph/sentence boundaries with overlap and
explicit common English exception/definition continuation markers. Chunk
boundaries are not a legal interpretation: verify generated chunk text against
the original document, especially for Amharic or other languages and long
multi-part rules.

`retrieve_legal_evidence(query, review_context, top_k, db=...)` is the shared
retrieval entry point for legal Q&A.
`LegalReviewContext` supports review date,
jurisdiction, language, source type, law number, and article filters. Review
dates constrain retrieval to known effective/end-date intervals; missing
dates and non-`current` legal statuses are surfaced as applicability
uncertainty. Unverified/rejected sources are excluded by default. The optional
`include_unverified` context flag is for controlled review only; such results
are never marked authoritative. Retrieval returns evidence and scores, not
compliance decisions or legal advice.

Retrieval unit tests use clearly labeled synthetic fixtures and an in-memory
mock embedding provider; no synthetic vector is presented as a real model
output.

## Legal questions API

Authenticated users can submit a question to
`POST /api/v1/legal-questions/answer` with a JSON body containing `question`
and an optional `review_context` using the fields described above. The
endpoint reuses legal evidence retrieval and the configured LLM provider. It
only sends evidence that is verified, marked current, and applicable to the
requested review date; requests cannot opt into unverified sources. Responses
include validated source/article references or an explicit
`insufficient_evidence` status. If eligible evidence exists but no LLM
provider is configured or it fails, the endpoint returns a service error
rather than a canned answer.

No legal corpus is bundled with the application; production answers require
independently verified source material in the existing legal-source registry.
The endpoint and its tests do not establish legal correctness.

Authenticated conversation history is available through
`POST /api/v1/legal-questions/conversations` to create a conversation or append
a question (include `conversation_id` to continue), `GET
/api/v1/legal-questions/conversations?limit=20&offset=0` to list the current
user's conversations, `GET /api/v1/legal-questions/conversations/{id}` to read
messages and citation snapshots, and `DELETE
/api/v1/legal-questions/conversations/{id}` to delete a conversation and its
messages. A new conversation returns `201`; appending returns `200`. Other
users' conversation IDs are treated as not found. Conversation messages and
answer citation details are snapshots; later legal-source edits do not rewrite
past responses.

Conversation follow-ups send a bounded recent transcript alongside retrieved
evidence. Their answer-cache keys include the owner scope and a digest of that
transcript, so private conversation-derived answers are not shared across
users or with the public-question endpoint. The transcript itself is not
stored in Redis. Conversation text is stored in the application's database
until the owner deletes the conversation; provider credentials and uploaded
file contents are not copied into conversation records.

Supported answers use Redis cache-aside before retrieval, embedding, or LLM
work. Cache keys are deterministic hashes of the normalized public question,
review context, configured provider/model versions, cache version, prompt
version, and a fingerprint of all legal-source, provision, and embedding-chunk
records. A source/provision review or content change, or a new/re-indexed
embedding chunk, therefore changes the knowledge-base fingerprint and makes
old entries unreachable. `LEGAL_QA_CACHE_VERSION` supports explicit manual
invalidation; increment it when answer logic or deployment-level configuration
changes in a way not otherwise represented in the key. `LEGAL_QA_CACHE_TTL_SECONDS`
defaults to 3600; setting it to 0 disables caching.

The cache is fail-open: Redis read/write errors are logged and the request
continues through normal retrieval and configured AI generation. It never
turns a Redis outage into a cached or hardcoded answer. Only validated,
supported answers are cached; insufficient-evidence results and failures are
not. Public endpoint cache entries contain public legal Q&A results only,
never full uploaded files. User identity is omitted only for public
questions whose answer depends exclusively on public legal sources and request
context; conversation answers use the owner-scoped key described above.

Administrative cache observability is available at
`GET /api/v1/admin/legal-question-cache/metrics` and
`GET /api/v1/health/answer-cache`; both require the server-side `admin` role.
Metrics are process-local and separate per application worker; they reset when
that process restarts and are not persisted. Hits are usable validated answers,
misses are lookups with no usable answer, and errors count failed Redis
get/set/delete/health-ping operations. Provider calls count actual generation
invocations; provider calls avoided count validated cache hits that returned
before generation, not billing telemetry. Logical invalidations count
knowledge-base version changes observed while generating cache keys after an
initial baseline; versioned keys make old answers unreachable, but the old
Redis entries are not physically deleted. The health endpoint reports Redis
reachability only and explicitly does not assess the AI system. No cache
statistics dashboard is exposed in the frontend.

To exercise the cache against a real Redis server locally, start Redis (for
example, `redis-server` in another terminal), then run from `backend/`:

```bash
LEGAL_QA_REDIS_INTEGRATION=1 REDIS_URL=redis://localhost:6379/0 \
  python -m pytest -q -m redis_integration \
  tests/integration/test_legal_question_cache_redis.py
```

The opt-in check includes a real cache-aside request flow: the first request
misses and calls retrieval plus a test-only generation provider, the equivalent
second request hits Redis and returns the same answer/citations without either
call, and changing a source record changes the knowledge-base version and
causes another miss. Its legal source and provider response are synthetic
test-only fixtures; it verifies cache mechanics, not legal accuracy or a live
LLM.

## Q&A test and evaluation layers

- **Unit/regression tests** use SQLite, mocks, or clearly labeled synthetic
  records; they cover evidence eligibility, citation validation, source
  versioning, cache ordering/isolation, and conversation ownership. Run the focused suite from `backend/`:

  ```bash
  python -m pytest -q -m unit \
    tests/test_legal_questions.py \
    tests/test_legal_retrieval.py \
    tests/test_legal_sources.py \
    tests/test_documents.py
  ```

- **External-service integration tests** are separately marked. The Redis
  check above requires a real Redis server. PostgreSQL/pgvector evaluation
  requires `LEGAL_QA_EVALUATION_DATABASE_URL` and an enabled pgvector extension.
- **Legal evaluation** is in `backend/tests/evaluation/`. Its dataset is an
  intentionally empty placeholder because no verified legal source material is
  bundled or otherwise available in this repository. Run the harness after
  adding independently verified and manually reviewed cases:

  ```bash
  cd backend
  LEGAL_QA_EVALUATION_DATABASE_URL='postgresql+psycopg://…' \
    python -m app.scripts.evaluate_legal_retrieval \
      --dataset tests/evaluation/dataset.json \
      --output evaluation-results.json
  ```

  Add `--include-end-to-end` to measure actual answer-service latency and Redis
  cache hits (requires configured QA services); use a `.csv` output suffix for
  per-case CSV. The benchmark compares baseline, BM25+vector RRF, and
  BM25+vector RRF with cross-encoder reranking. It reports Recall@5,
  Precision@5, MRR, nDCG@5, retrieval latency, and optional end-to-end latency
  and observed cache hit rate. Until reviewed cases are provided and the
  benchmark is run, no legal evaluation score or improvement is reported.
- **Manual legal review** is a separate required activity, described in
  `backend/tests/evaluation/README.md`. Automated tests do not establish legal
  correctness.

Run its focused tests with:

```bash
cd backend
python -m pytest tests/test_legal_questions.py
```

## Legacy audit data

The contract-audit API and worker have been removed. Existing audit database
records and migration history are retained; this cleanup does not drop tables
or delete saved data. Redis remains in use for request rate limiting and
optional legal-Q&A answer caching. User-uploaded legal documents still feed the
RAG knowledge base, and changes to those documents invalidate cached answers.

## Security posture and production checklist

Implemented safeguards include Argon2id password hashing, normalized unique
emails, hashed revocable random bearer tokens, protected endpoints, explicit
organization membership checks, private local file storage, upload signature
and MIME checks, bounded uploads and pagination, source verification gates,
parameterized SQLAlchemy retrieval, strict model-output schemas, server-side
citation validation, safe generic 500 responses, and Redis-backed limits on
login, uploads, and source ingestion. No cookies are
used, so browser CSRF protections are not applicable to the bearer-token API;
CORS does not allow credentials. Request IDs are validated or replaced and
included in structured logs. Contract contents, credentials, and exception
stack traces are not intentionally logged.

Before production:

- Set `APP_ENVIRONMENT=production`, use HTTPS end-to-end, and configure
  `CORS_ORIGINS` to exact trusted origins. Wildcard origins are rejected.
  Production mode disables interactive API documentation.
- Store database, Redis, embedding, and LLM credentials in a secret manager;
  use TLS/private networking for PostgreSQL and Redis. Do not commit `.env`.
- Configure Redis availability and persistence/monitoring. Rate limiting fails
  closed (503) when Redis is unavailable. Limits are per direct peer IP; if
  running behind a proxy, configure a trusted proxy boundary before accepting
  forwarded client IP headers.
- Use private, encrypted, access-controlled object storage for multiple
  production workers. The included local storage is intended for development
  and single-host deployment.
- Verify backup, retention, and deletion policy. Document deletion removes the
  file and soft-deletes metadata; no automated retention/purge schedule or
  orphan-file reconciliation job is implemented.
- Approve the LLM/embedding vendors for confidential legal data and
  review their retention and residency terms. The app does not claim model
  accuracy or legally validated conclusions. Remote provider URLs must use
  HTTPS; unauthenticated HTTP is allowed only for loopback development.
- Apply migrations and run tests on the actual PostgreSQL/pgvector and Redis
  versions used in production. Local automated checks used SQLite and did not
  test managed-service permissions, network failures, or multi-worker load.

Security tests and available regression tests are run with:

```bash
cd backend
python -m pytest
```

The full test suite includes synthetic legal fixtures and mock legal-answer
providers; it is not a penetration test or legal validation. PDF-dependent
tests require PyMuPDF to be installed.
