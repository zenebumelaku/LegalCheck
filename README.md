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

This setup intentionally does not include contract uploads, RAG, or
audit-processing logic. The database schema includes the foundational audit
and finding records, but does not implement analysis workflows. Embeddings and
vector retrieval are deferred to Part 6. Legal-source status is initialized
to `unknown`; records are not considered current unless their status and
verification are established explicitly.

# LegalCheck

# LegalCheck
