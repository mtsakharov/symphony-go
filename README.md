# FastAPI Service

FastAPI service for health monitoring and user management. The project uses a `src/` layout, SQLAlchemy for persistence, Alembic for schema migrations, and `uv` for dependency management.

## What It Provides

- Liveness and readiness probes under `/api/v1/health`
- CRUD endpoints for users under `/api/v1/users`
- OpenAPI schema plus Swagger UI and ReDoc
- PostgreSQL-backed runtime configuration
- Test coverage for API and service-layer behavior

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- `uv`
- Pytest, Ruff, MyPy

## Requirements

- Python 3.12+
- `uv`
- Docker and Docker Compose for the local PostgreSQL service

## Local Development

1. Install dependencies:

```bash
uv sync
```

2. Create a local environment file:

```bash
cp .env.example .env
```

3. Start PostgreSQL:

```bash
docker compose up -d postgres
```

4. Apply the database migration:

```bash
uv run alembic upgrade head
```

5. Start the API:

```bash
uv run serve
```

The service listens on `http://localhost:8000`.

## Configuration

Application settings are loaded from `.env`. Defaults are defined in [`src/app/core/config.py`](src/app/core/config.py).

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `FastAPI Service` | Display name used by FastAPI/OpenAPI |
| `APP_VERSION` | `1.0.0` | API version reported in readiness and docs |
| `ENVIRONMENT` | `dev` | Environment label exposed in the OpenAPI `servers` metadata |
| `DEBUG` | `false` | Enables reload mode when running `uv run serve` |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `API_V1_PREFIX` | `/api/v1` | Prefix for versioned API routes |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service` | SQLAlchemy connection string |

## API Surface

### Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

### Health Endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

Example:

```bash
curl http://localhost:8000/api/v1/health/ready
```

### Users Endpoints

- `POST /api/v1/users`
- `GET /api/v1/users?page=1&limit=20`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

Example create request:

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ada@example.com",
    "first_name": "Ada",
    "last_name": "Lovelace"
  }'
```

The service enforces unique email addresses and returns:

- `409 Conflict` when a duplicate email is submitted
- `404 Not Found` when a user does not exist

## Database and Migrations

The runtime configuration expects PostgreSQL. The repository includes one Alembic migration that creates the `users` table with a unique `email` constraint.

Useful commands:

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Quality Checks

Run the standard checks with either `uv` or `make`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
```

```bash
make test
make lint
make fmt
make typecheck
make migrate
```

Tests use a temporary SQLite database created by [`tests/conftest.py`](tests/conftest.py), so they do not require the Docker PostgreSQL instance.

## Docker

To run the full stack in containers:

```bash
docker compose up --build
```

This starts both PostgreSQL and the API container defined in [`docker-compose.yml`](docker-compose.yml).

## Project Layout

```text
.
├── alembic/                 # Database migration configuration and revisions
├── src/app/
│   ├── api/                 # Route registration and versioned endpoints
│   ├── core/                # Settings, logging, and lifespan hooks
│   ├── database/            # SQLAlchemy base, models import, and session setup
│   └── users/               # User models, schemas, repository, and service layer
├── tests/                   # API and service tests
├── Dockerfile
├── Makefile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```
