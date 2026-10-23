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

## Scope boundary

This setup intentionally does not include authentication, contract uploads,
RAG, or audit-processing logic. The database schema includes the foundational
audit and finding records, but does not implement analysis workflows.
Embeddings and vector retrieval are deferred to Part 6. Legal-source status is
initialized to `unknown`; records are not considered current unless their
status and verification are established explicitly.

# LegalCheck

# LegalCheck
