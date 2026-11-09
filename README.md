# LegalCheck Ethiopia

Backend foundation for the LegalCheck Ethiopia employment-contract compliance
platform. The initial setup provides a versioned FastAPI application, health
checks, environment-based settings, CORS configuration, centralized errors,
and structured JSON logs.

## Requirements

- Python 3.11 or newer
- PostgreSQL with pgvector for the application database and semantic retrieval
- Redis for rate limiting, the audit job queue, and optional answer caching
- Node.js/npm only when building or running the React frontend

The API and database are required for normal application use. Redis is required
for protected rate-limited operations and queued contract audits: rate limiting
fails closed if Redis is unavailable. Run the audit worker to process queued
audits; without it, queued audits will not be processed. Embeddings and LLM
generation are optional integrations, but an answerable legal Q&A request
requires eligible indexed legal sources and an available configured LLM provider.

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

Start Redis separately, for example with `redis-server`. `REDIS_URL` must point
to the same Redis service for the API and worker. Do not reuse development
database or Redis URLs in production.

## Run the application

With the virtual environment activated and the shell in `backend/`:

```bash
uvicorn app.main:app --reload
```

The interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

Run the separate audit worker in another terminal, with the same backend
environment and dependencies:

```bash
cd backend
source .venv/bin/activate
python -m app.workers.audit_worker
```

The API enqueues contract audits; the RQ worker consumes them. Legal Q&A is
served directly by the API and does not use this audit queue.

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
`LLM_PROVIDER=openai_compatible` or `LLM_PROVIDER=ollama`, plus the provider's
`LLM_API_URL`, `LLM_MODEL_NAME`, and optional `LLM_API_KEY` as appropriate.
Ollama requires a separately installed/running server and available model.
Remote endpoints must follow the application's HTTPS rules; unauthenticated
HTTP is limited to loopback development endpoints. If the provider is disabled,
missing, rate-limited, or unavailable, legal Q&A returns a clear error; it
never substitutes a sample answer. No paid provider is bundled or required for
startup.

Embeddings are independently optional. `EMBEDDING_PROVIDER=disabled` uses
non-semantic retrieval only. Configure the supported OpenAI-compatible
embedding endpoint, or explicitly install and provision the optional local
Sentence Transformers model as described in
[Legal retrieval and embeddings](#legal-retrieval-and-embeddings). The local
model is not downloaded during ordinary startup or tests. Embedding model
versions must remain compatible with the database's 384-dimensional vectors;
re-index when intentionally changing the model version.

## Answer cache configuration

The answer cache uses the same `REDIS_URL` as queues/rate limits, but stores
legal Q&A responses under a separate key namespace.
`LEGAL_QA_CACHE_TTL_SECONDS` defaults to 3600 seconds; setting it to `0`
disables answer caching without disabling Redis-backed rate limiting or audit
queues. `LEGAL_QA_CACHE_VERSION` defaults to `v1`; increment it to make old
answer keys unreachable after answer-logic or configuration changes not already
included in the key. Legal-source/provision/index changes update the knowledge
base fingerprint automatically. Old versioned entries expire by TTL and are
not physically deleted at invalidation time.

Redis cache read/write failures are fail-open for Q&A: the request continues to
retrieval and generation and does not return a fabricated answer. This is
separate from rate limiting, which fails closed when Redis is unavailable.

## Deployment configuration

The repository's existing [`render.yaml`](./render.yaml) describes a Render
web API, a separate audit worker, PostgreSQL, and a Redis-compatible service.
It is a hosting blueprint, not a deployment verification: it has not been
deployed or tested against a Render account. It runs migrations in the API
build command and starts the API and worker with their respective commands.
The frontend is not deployed by that blueprint and needs a separate static
frontend deployment with `VITE_API_BASE_URL` pointing to the API.

The blueprint sets both LLM and embedding providers to `disabled`. API startup
can succeed in that state, but answer generation returns an explicit
unavailable-provider error, and audit analysis cannot produce AI findings.
Configure supported providers using the hosting platform's secret/environment
settings before relying on those features. Confirm PostgreSQL pgvector
availability and migration permissions for the selected database plan.

The blueprint configures local private-file storage. [Render persistent
disks](https://render.com/docs/disks) attach to a specific service; the API's
disk is not shared with the worker's disk even if their names and
`PRIVATE_STORAGE_PATH` values match. Contract
audits require the worker to access the exact private files uploaded by the
API. Replace local storage with an approved shared private object store, or
otherwise provide a verified shared-storage implementation, before using
multi-service audits. Do not treat the current local-storage blueprint as
production-ready for contract files.

This repository intentionally has no Docker Compose setup. For local
development, start PostgreSQL with pgvector and Redis using the host's supported
installation, then follow the migration/API/worker commands above. No
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
metadata to preserve audit foreign keys. If physical cleanup fails, the API
reports that cleanup is pending while leaving the metadata soft-deleted.

An authenticated legal-question endpoint provides preliminary,
evidence-grounded AI answers when eligible legal sources and an LLM provider
are available. It abstains when evidence is absent or uncertain; it does not
make legal judgments. Contract audit analysis is a separate workflow.
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

The retrieval layer uses PostgreSQL `pgvector` plus PostgreSQL full-text search.
Apply the latest Alembic migration after installing PostgreSQL with pgvector
available:

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

`retrieve_legal_evidence(query, review_context, top_k, db=...)` combines exact
article matching, keyword retrieval, and semantic ranking when a compatible
provider is configured. A reranker may be supplied through its interface;
none is enabled by default. `LegalReviewContext` supports review date,
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

This endpoint does not read contract documents or create audits. No legal
corpus is bundled with the application; production answers require
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
until the owner deletes the conversation; provider credentials, audit content,
and contract documents are not copied into conversation records.

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
never contract text or audit output. User identity is omitted only for public
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
  versioning, cache ordering/isolation, conversation ownership, and audit/cache
  separation. Run the focused suite from `backend/`:

  ```bash
  python -m pytest -q -m unit \
    tests/test_legal_questions.py \
    tests/test_legal_retrieval.py \
    tests/test_legal_sources.py \
    tests/test_audits.py \
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
    python -m pytest -q -m 'legal_evaluation and postgres_integration' \
    tests/evaluation
  ```

  Until then the harness skips; no legal evaluation score is reported.
- **Manual legal review** is a separate required activity, described in
  `backend/tests/evaluation/README.md`. Automated tests do not establish legal
  correctness.

Run its focused tests with:

```bash
cd backend
python -m pytest tests/test_legal_questions.py
```

## Contract analysis

The analysis service is separate from API routes and is invoked with an
existing pending `Audit`, its database session, private storage implementation,
and an LLM provider. It extracts candidate English-language paragraphs for
duration, compensation, working hours, leave, probation, termination, notice,
confidentiality, and signatures. It preserves extracted wording and available
page/paragraph references. Keyword extraction is a candidate finder, not proof
that all clauses were found. If locally configured, the shared document
extraction path can use Tesseract for scanned PDF pages; OCR output is
fallible and is included with processing warnings.

AI analysis is disabled unless explicitly configured. To use an approved
OpenAI-compatible provider, set these values privately in `backend/.env` or a
secret manager:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_API_URL=https://your-provider.example/v1
LLM_API_KEY= # optional only for an unauthenticated private endpoint
LLM_MODEL_NAME=your-approved-model
LLM_MODEL_VERSION=provider-model-revision
LLM_TIMEOUT_SECONDS=90
MAX_CONTRACT_ANALYSIS_CHARACTERS=500000
```

The provider URL may be a base `/v1` URL (the service appends
`/chat/completions`) or a full `/chat/completions` URL. The service sends
extracted contract clauses and retrieved legal evidence to that provider.
Use only a provider approved to process confidential contract data; keep keys
server-side and never commit them. The provider must return a JSON object with
the fields validated by `LLMClauseAnalysis`; invalid or unavailable provider
responses fail the audit rather than completing it.

An optional local Ollama adapter also uses the existing LLM interface and is
available to both contract analysis and legal Q&A. Install and start Ollama,
explicitly install the model you choose with Ollama, then configure:

```dotenv
LLM_PROVIDER=ollama
LLM_API_URL=http://localhost:11434
LLM_MODEL_NAME=your-installed-model
LLM_MODEL_VERSION=your-model-revision
```

The adapter calls Ollama's local `/api/chat` endpoint with a bounded response
size and the configured timeout. It does not install models or start Ollama.
An unavailable service or missing model is reported as unavailable; rate
limits are reported distinctly. `LLM_PROVIDER=disabled` remains the default,
and no example answer is returned if generation is unconfigured or fails.
Local inference depends on the selected model and host resources; no free-tier,
quota, or quality guarantee is implied. The existing
`openai_compatible` provider remains available for externally configured
services. Both options keep credentials server-side and require HTTPS for
remote endpoints; unauthenticated HTTP is permitted only on loopback.

For an integration from a trusted workflow, call `analyze_audit(audit_id,
db=..., storage=..., llm_provider=...)` from
`backend/app/services/compliance_analysis.py`. The returned `FinalAuditAnalysis`
includes limitations and evidence metadata. The service persists findings only
after validation. A citation must identify a provision returned by retrieval,
match its source/article/sub-article, cite a source eligible for findings, and
quote a substring of the saved provision text. Unsupported or uncertain
citations downgrade the result to `insufficient_evidence`; provider failures
record a safe failure code and do not mark the audit completed. The existing
finding confidence column remains unset because model self-confidence is not
calibrated as a probability.

There is no verified, versioned Ethiopian employment-law rule set configured,
so this module performs no deterministic legal-compliance checks and does not
provide definitive legal advice. Review results and cited sources with a
qualified Ethiopian legal professional. Unit tests use synthetic fixtures and
mock providers; they do not validate a model or legal interpretation:

```bash
cd backend
python -m pytest tests/test_compliance_analysis.py
```

## Audit workflow and worker

Audits are created from an existing, non-deleted PDF or DOCX document. The
requester must own a personal document or have an allowed membership in its
organization. Audit details, status, and findings repeat those access checks;
organization documents require an active membership for each request. Audit
creation returns `202 Accepted` with a queued status.

Processing uses Redis and RQ. Start PostgreSQL and Redis, apply migrations, and
run the API and worker in separate terminals:

```bash
# Terminal 1: PostgreSQL and Redis must be available.
redis-server

# Terminal 2
cd backend
alembic upgrade head
python -m app.workers.audit_worker

# Terminal 3
cd backend
uvicorn app.main:app --reload
```

Configure `DATABASE_URL` and `REDIS_URL` in `backend/.env`. The worker also
needs the same private-storage configuration and an enabled LLM provider to
complete analysis. It reads documents only through the configured private
storage abstraction. Audit states progress through `queued`, `extracting`,
`retrieving_sources`, `analyzing`, `generating_report`, and `completed`, or
`failed`. Extraction warnings are retained on the audit. Findings and the
completed state are committed atomically; failed processing does not leave
partial findings.

RQ jobs have a configurable timeout (`AUDIT_JOB_TIMEOUT_SECONDS`, default
30 minutes). A worker crash can leave an audit in an active state; after the
configured stale threshold (`AUDIT_STALE_AFTER_SECONDS`, default 35 minutes),
an authorized user may call `POST /api/v1/audits/{audit_id}/retry`. Failed
audits can also be explicitly retried. Retries are rejected if findings were
already persisted. Workers claim only queued audits with a conditional database
update, so duplicate job delivery cannot start a second run. A Redis enqueue
failure is recorded as a failed audit and can be retried when Redis is
available.

Example audit request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/audits \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"<owned-document-uuid>","review_options":{"jurisdiction":"ET","review_date":"2026-10-24"}}'
```

Poll `GET /api/v1/audits/{audit_id}/status` and retrieve completed findings
from `GET /api/v1/audits/{audit_id}/findings`. Analysis still requires a
configured provider and verified applicable legal sources for supported
citations; it does not imply legal advice. Integration tests use a test-only
mock analyzer that only emits an insufficient-evidence outcome when no
authoritative fixture is available. To run them:

```bash
cd backend
python -m pytest tests/test_audits.py tests/test_compliance_analysis.py
```

## Audit reports and finding feedback

Completed audits provide a saved-result JSON report at
`GET /api/v1/audits/{audit_id}/report` and a downloadable PDF at
`GET /api/v1/audits/{audit_id}/report.pdf`. Both routes use the same document
ownership and organization-membership checks as audit findings; responses are
private and non-cacheable. They read the stored audit, finding, and citation
records and never rerun extraction or an AI provider. Citation source title,
version, URL, article reference, and provision text are snapshotted when a new
finding is saved so later registry changes do not silently rewrite that
report. Existing citations without snapshots use their linked source records.

Users with access to a completed audit can submit feedback through
`POST /api/v1/findings/{finding_id}/feedback`. Supported categories are
`incorrect_finding`, `incorrect_citation`, `missing_issue`, and `other`;
`other` requires a description, and descriptions are limited to 5,000
characters.

PDF output uses ReportLab. The built-in PDF font can render its supported
Western character set. The repository does not bundle an Ethiopic font.
For Amharic or other scripts outside that encoding, configure
`REPORT_UNICODE_FONT_PATH` to a server-installed, licensed TrueType `.ttf` font
that contains every character in the report. The font is embedded in generated
PDFs. If no configured font covers the report's characters, the PDF endpoint
returns a clear service-unavailable response instead of silently replacing
characters; the JSON report preserves Unicode text. ReportLab does not perform
complex-script shaping, so verify the chosen font and rendered output with
native-language reviewers before production.

## Security posture and production checklist

Implemented safeguards include Argon2id password hashing, normalized unique
emails, hashed revocable random bearer tokens, protected endpoints, explicit
organization membership checks, private local file storage, upload signature
and MIME checks, bounded uploads and pagination, source verification gates,
parameterized SQLAlchemy retrieval, strict model-output schemas, server-side
citation validation, safe generic 500 responses, and Redis-backed limits on
login, uploads/source ingestion, audit creation, and retry. No cookies are
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
  file and soft-deletes metadata while preserving audits; no automated
  retention/purge schedule or orphan-file reconciliation job is implemented.
- Approve the LLM/embedding vendors for confidential contract/legal data and
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

The full test suite includes synthetic legal fixtures and mock analysis
providers; it is not a penetration test or legal validation. PDF-dependent
tests require PyMuPDF to be installed.
