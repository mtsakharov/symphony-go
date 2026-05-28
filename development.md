# Development Guide

This project uses `uv` for dependency management, FastAPI for the API layer, SQLAlchemy for persistence, and Alembic for schema migrations.

## Local Setup

1. Install Python 3.12 and [`uv`](https://docs.astral.sh/uv/).
2. Sync dependencies:

   ```bash
   uv sync
   ```

3. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

4. Start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

5. Apply migrations:

   ```bash
   uv run alembic upgrade head
   ```

6. Start the API:

   ```bash
   uv run serve
   ```

The application listens on `http://localhost:8000`.

## Environment Variables

The application reads configuration from `.env` via `pydantic-settings`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `FastAPI Service` | OpenAPI and application display name |
| `APP_VERSION` | `1.0.0` | Application version exposed by the API |
| `ENVIRONMENT` | `dev` | Runtime environment label |
| `DEBUG` | `false` | Enables uvicorn reload mode when `true` |
| `HOST` | `0.0.0.0` | Bind host for the API server |
| `PORT` | `8000` | Bind port for the API server |
| `API_V1_PREFIX` | `/api/v1` | Versioned API prefix |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service` | SQLAlchemy connection string |

## Common Commands

Use either the raw `uv` commands or the `Makefile` targets below.

| Purpose | Command | Make target |
| --- | --- | --- |
| Install dependencies | `uv sync` | `make sync` |
| Run the API | `uv run serve` | `make run` |
| Apply migrations | `uv run alembic upgrade head` | `make migrate` |
| Run tests | `uv run pytest` | `make test` |
| Run lint checks | `uv run ruff check .` | `make lint` |
| Format code | `uv run ruff format .` | `make fmt` |
| Type-check source | `uv run mypy src` | `make typecheck` |

If you want stricter local verification, run:

```bash
uv run mypy src tests
```

## Testing

The test suite uses `pytest`, `pytest-asyncio`, and `httpx` against the FastAPI ASGI app. Tests create a temporary SQLite database and override the app database dependency, so they do not require the local PostgreSQL container.

Run the full suite with:

```bash
uv run pytest
```

## Database and Migrations

The default local database is PostgreSQL from `docker-compose.yml`. Alembic migrations live in `alembic/versions`.

Apply the latest migration:

```bash
uv run alembic upgrade head
```

Create a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

## API Reference During Development

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## Container Workflow

To build and run the API service together with PostgreSQL:

```bash
docker compose up --build
```
