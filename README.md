git remote add origin https://github.com/zenebumelaku/LegalCheck.git
git branch -M main
git push -u origin main# LegalCheck Ethiopia

Backend foundation for the LegalCheck Ethiopia employment-contract compliance
platform. The initial setup provides a versioned FastAPI application, health
checks, environment-based settings, CORS configuration, centralized errors,
and structured JSON logs.

## Requirements

- Python 3.11 or newer
- PostgreSQL for the readiness check

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

## Run the application

With the virtual environment activated and the shell in `backend/`:

```bash
uvicorn app.main:app --reload
```

The interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

## Database migrations

With PostgreSQL running and `DATABASE_URL` set in `.env`, from `backend/`:

```bash
alembic upgrade head
```

Apply this migration before starting the API so the `auth_sessions` table and
case-insensitive email index exist.

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

Uploads accept PDF and DOCX only. PDFs with little/no text include a scanned
document warning. OCR is not bundled; setting `OCR_ENABLED=true` currently
reports that no OCR provider is integrated and does not execute OCR. DOCX page
numbers are not available from the document structure, so extraction includes
paragraph references without inventing page numbers. Delete removes the
private file and soft-deletes metadata to preserve audit foreign keys. If
physical cleanup fails, the API reports that cleanup is pending while leaving
the metadata soft-deleted.

This setup does not implement RAG or legal analysis. The database schema
includes foundational audit and finding records, but not analysis workflows.
Retrieval supplies evidence candidates only; final legal judgments remain
deferred. Legal-source status is initialized to `unknown`; records are not
considered current unless their status and verification are established
explicitly.

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

Once a source has passed the registry's independent verification workflow,
generate its embeddings with:

```bash
cd backend
python -m app.scripts.generate_legal_embeddings
python -m app.scripts.generate_legal_embeddings --source-id <verified-source-uuid>
```

The script indexes only sources with `verification_status=verified`. It
preserves source version, article, sub-article, heading, and page references in
chunks. Provisions remain intact when they fit the configured chunk window;
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

## Contract analysis

The analysis service is separate from API routes and is invoked with an
existing pending `Audit`, its database session, private storage implementation,
and an LLM provider. It extracts candidate English-language paragraphs for
duration, compensation, working hours, leave, probation, termination, notice,
confidentiality, and signatures. It preserves extracted wording and available
page/paragraph references. Keyword extraction is a candidate finder, not proof
that all clauses were found; OCR is not implemented by this analysis module.

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
