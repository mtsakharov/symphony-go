# FastAPI Service

Small FastAPI service with health probes, versioned REST endpoints for user management, SQLAlchemy persistence, and Alembic migrations.

## Features

- FastAPI app served with Uvicorn
- Versioned API under `/api/v1`
- Health endpoints for liveness and readiness checks
- Users CRUD API with pagination and duplicate-email protection
- PostgreSQL-backed persistence with Alembic migrations
- `uv`-managed dependencies and a small Make-based developer workflow

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Docker and Docker Compose for local PostgreSQL

## Project Layout

```text
.
├── alembic/                # Database migrations
├── src/app/
│   ├── api/                # API routers and endpoints
│   ├── core/               # Settings, lifespan, logging
│   ├── database/           # SQLAlchemy setup
│   ├── users/              # User models, schemas, service layer
│   └── main.py             # FastAPI application entrypoint
├── tests/                  # API and service tests
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## Local Setup

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

4. Apply database migrations:

```bash
uv run alembic upgrade head
```

5. Run the API:

```bash
uv run serve
```

The service listens on `http://localhost:8000`.

## Configuration

The app reads settings from `.env`. Defaults from `.env.example`:

| Variable | Default |
| --- | --- |
| `APP_NAME` | `FastAPI Service` |
| `APP_VERSION` | `1.0.0` |
| `ENVIRONMENT` | `dev` |
| `DEBUG` | `false` |
| `HOST` | `0.0.0.0` |
| `PORT` | `8000` |
| `API_V1_PREFIX` | `/api/v1` |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_service` |

## API Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## Common Commands

```bash
make sync       # install dependencies
make run        # start the API
make migrate    # apply Alembic migrations
make lint       # ruff check
make fmt        # ruff format
make typecheck  # mypy src
make test       # pytest
```

Equivalent direct commands:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src tests
uv run pytest
```

## API Summary

### Health

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

Example:

```bash
curl http://localhost:8000/api/v1/health/ready
```

### Users

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

Update a user:

```bash
curl -X PATCH http://localhost:8000/api/v1/users/<user_id> \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Janet",
    "is_active": false
  }'
```

The API returns:

- `201` when a user is created
- `404` when a requested user does not exist
- `409` when a create or update would reuse an existing email address

## Running With Docker

```bash
docker compose up --build
```

This starts PostgreSQL and the API service together using the `.env` file.
