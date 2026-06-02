# FastAPI Service

## Overview

FastAPI service with versioned health probes, a users CRUD API, Alembic migrations, and generated OpenAPI docs.

## Prerequisites

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- Docker, only if you want to run the local PostgreSQL container

## Setup

Use the checked-in Compose file to start PostgreSQL for local development, then run the app from the host environment:

```bash
uv sync
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
```

## Run

```bash
uv run serve
```

The API listens on `http://localhost:8000`.

## Validation

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest
```

Optional formatting helper:

```bash
uv run ruff format .
```

Make aliases are available for the same workflows:

```bash
make sync
make run
make lint
make fmt
make typecheck
make test
make migrate
```

## Related Docs

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`
- Health endpoints: `GET /api/v1/health/live`, `GET /api/v1/health/ready`
- Users API: `POST`, `GET`, `PATCH`, and `DELETE` under `/api/v1/users`
