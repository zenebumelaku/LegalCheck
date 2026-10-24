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
until an email provider is configured. Rate limiting is not configured in this
application; deploy login, registration, and reset endpoints behind an
appropriately configured rate limiter or API gateway.

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
