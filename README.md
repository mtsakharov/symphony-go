# FastAPI Service

FastAPI service for health probes and user management, built with Python 3.12, SQLAlchemy, Alembic, and `uv`.

## Features

- Versioned API mounted under `/api/v1`
- Health endpoints for liveness and readiness checks
- CRUD endpoints for users with pagination and duplicate-email protection
- Alembic migrations for database schema changes
- `uv`, `pytest`, `ruff`, and `mypy` based development workflow
- Optional Docker Compose setup for local PostgreSQL

## Requirements

- Python 3.12
- [`uv`](https://github.com/astral-sh/uv)
- Docker and Docker Compose, if you want to run PostgreSQL locally in a container

## Project Layout

```text
.
├── alembic/                  # Database migration environment and revisions
├── src/app/
│   ├── api/                  # FastAPI routers and versioned endpoints
│   ├── core/                 # Settings, logging, and application lifespan
│   ├── database/             # SQLAlchemy engine, sessions, and model registration
│   ├── users/                # User models, schemas, repository, and service layer
│   └── main.py               # FastAPI app factory and uvicorn entrypoint
├── tests/                    # API and service tests
├── docker-compose.yml        # Local PostgreSQL service
├── Dockerfile                # Container image for the API
├── Makefile                  # Common development commands
└── pyproject.toml            # Project metadata and tool configuration
```

## Configuration

Settings are loaded from environment variables and `.env`. Start from the checked-in example:

```bash
cp .env.example .env
```

Available settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `FastAPI Service` | OpenAPI/application title |
| `APP_VERSION` | `1.0.0` | Reported service version |
| `ENVIRONMENT` | `dev` | Environment label exposed in OpenAPI server metadata |
| `DEBUG` | `false` | Enables uvicorn reload when `true` |
| `HOST` | `0.0.0.0` | Bind host for the API server |
| `PORT` | `8000` | Bind port for the API server |
| `API_V1_PREFIX` | `/api/v1` | Prefix used for versioned routes |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service` | SQLAlchemy database connection string |

## Quick Start

Install dependencies:

```bash
uv sync
```

Start PostgreSQL with Docker Compose:

```bash
docker compose up -d postgres
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Run the API:

```bash
uv run serve
```

The service will listen on `http://localhost:8000`.

## Running with Docker

To build and run the full stack with Docker:

```bash
docker compose up --build
```

This starts:

- `postgres` on `localhost:5432`
- `fastapi-service` on `http://localhost:8000`

## API Documentation

Once the server is running:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## API Overview

### Health endpoints

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

Example:

```bash
curl http://localhost:8000/api/v1/health/live
```

```json
{
  "status": "ok",
  "timestamp": "2026-05-26T12:00:00Z"
}
```

### Users endpoints

Base path: `/api/v1/users`

- `POST /api/v1/users`
- `GET /api/v1/users?page=1&limit=20`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

Create a user:

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  }'
```

List users:

```bash
curl "http://localhost:8000/api/v1/users?page=1&limit=20"
```

The API returns:

- `201` for successful user creation
- `404` when a user does not exist
- `409` when an email address already exists

## Development

Common commands:

```bash
make sync
make run
make test
make lint
make fmt
make typecheck
make migrate
```

Equivalent direct `uv` commands:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run alembic upgrade head
```

## Testing

Test coverage includes:

- API health checks
- User CRUD API behavior
- Service-layer user operations

Run the test suite with:

```bash
uv run pytest
```

Tests use a temporary SQLite database, so they do not require the local PostgreSQL container.
