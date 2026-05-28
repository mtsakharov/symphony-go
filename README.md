# FastAPI Service

FastAPI user-management service with versioned REST endpoints, health probes, SQLAlchemy persistence, and Alembic migrations.

## Features

- FastAPI application served from `src/app`
- Versioned API routes under `/api/v1`
- Health endpoints for liveness and readiness checks
- User CRUD endpoints backed by SQLAlchemy
- Alembic migrations for schema changes
- `uv`-managed dependencies and task runner commands
- Pytest coverage for API and service behavior

## Requirements

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Docker, if you want PostgreSQL through `docker compose`

## Quick Start

### Option 1: PostgreSQL via Docker

```bash
uv sync
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
uv run serve
```

The API starts at `http://localhost:8000`.

### Option 2: Local SQLite for quick development

If you do not want to run PostgreSQL locally, point `DATABASE_URL` at SQLite instead:

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run serve
```

Set this value in `.env` before running migrations:

```dotenv
DATABASE_URL=sqlite:///./fastapi_service.db
```

SQLite works for local development because the SQLAlchemy engine enables the required `check_same_thread` setting automatically when `DATABASE_URL` starts with `sqlite`.

## Configuration

Settings are loaded from `.env` by `app.core.config.Settings`.

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_NAME` | `FastAPI Service` | OpenAPI title and application name |
| `APP_VERSION` | `1.0.0` | Returned by readiness checks and docs |
| `ENVIRONMENT` | `dev` | Supported values: `dev`, `staging`, `prod` |
| `DEBUG` | `false` | Enables uvicorn reload when true |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `API_V1_PREFIX` | `/api/v1` | Base prefix for versioned endpoints |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service` | SQLAlchemy connection string |

## Running The Service

```bash
uv run serve
```

OpenAPI assets are exposed at:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## API Summary

### Health

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

Example liveness request:

```bash
curl http://localhost:8000/api/v1/health/live
```

Example readiness request:

```bash
curl http://localhost:8000/api/v1/health/ready
```

### Users

Base path: `/api/v1/users`

- `POST /api/v1/users`
- `GET /api/v1/users?page=1&limit=20`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

Example create request:

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "user@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  }'
```

The API enforces unique email addresses, returns `404` for missing users, and supports pagination with `page` and `limit` query parameters.

## Development

Install dependencies once:

```bash
uv sync
```

Common commands:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```

Equivalent `make` targets:

```bash
make sync
make run
make lint
make fmt
make typecheck
make test
make migrate
```

The test suite uses a temporary SQLite database configured in `tests/conftest.py`, so tests can run without PostgreSQL.

## Docker

Start PostgreSQL only:

```bash
docker compose up -d postgres
```

Start the full stack:

```bash
docker compose up --build
```

The Docker image runs `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000` and includes a health check against `/api/v1/health/live`.

## Project Structure

```text
.
├── alembic/
│   └── versions/
├── src/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       └── endpoints/
│       ├── core/
│       ├── database/
│       ├── users/
│       └── main.py
├── tests/
│   ├── api/
│   │   └── v1/
│   ├── services/
│   └── conftest.py
├── .env.example
├── Dockerfile
├── Makefile
├── README.md
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```
