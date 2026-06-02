# README Workflow Audit

## Scope

This repository is a single FastAPI service, not a monorepo. The workflow sources live in root-level repo artifacts plus service code under `src/app/`, `alembic/`, and `tests/`. No `.github/` workflow files, alternate task runners, or additional service-level setup docs were found.

## Source of Truth

| Artifact | What it controls | Notes for README follow-up |
| --- | --- | --- |
| `.python-version` | Local Python version pin (`3.12`) | Aligns with the Python 3.12 toolchain used across the repo. |
| `pyproject.toml` | Python requirement (`>=3.12`), dependencies, dev tools, pytest config, Ruff config, MyPy config, and the `serve` entrypoint | This is the canonical source for package/runtime metadata. `uv.lock` should be treated as the companion lockfile for dependency resolution. |
| `Makefile` | Wrapper commands: `sync`, `run`, `test`, `lint`, `fmt`, `typecheck`, `migrate` | These are shorthands over `uv` commands, not separate workflows. |
| `.env.example` | Documented app env vars and default `DATABASE_URL` | Default DB host is `localhost`, which fits host-based development but not the app container in Compose. |
| `src/app/core/config.py` | Actual settings loading rules and defaults | Confirms settings come from `.env` and that `DATABASE_URL` defaults to host-local Postgres. |
| `alembic.ini` and `alembic/env.py` | Migration config and DB URL sourcing | `alembic.ini` has a Postgres fallback, but `alembic/env.py` overrides it with application settings from `.env`/defaults. |
| `src/app/main.py` | Application entrypoint and the `serve` command target | `uv run serve` is the canonical host run command. |
| `src/app/api/v1/endpoints/health.py` and `src/app/core/lifespan.py` | Meaning of liveness/readiness endpoints | Readiness reports application startup state only; it is not a DB connectivity check. |
| `Dockerfile` | Container image build and runtime command | Builds the service image and runs `uvicorn app.main:create_app --factory`. |
| `docker-compose.yml` | Optional containerized workflow | Defines `postgres` and `fastapi-service`, and passes `.env` into the app container unchanged. |
| `tests/conftest.py` | Test database behavior | Tests override the DB dependency with a temporary SQLite database, so Postgres is not required for `pytest`. |
| `README.md` | Existing prose docs | Use as a reconciliation target only; do not treat it as authoritative where it diverges from executable artifacts. |

## Canonical Commands for README

### Primary developer path

Use the host-based `uv` workflow as the primary README path:

```bash
uv sync
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
uv run serve
```

Why this path is canonical:

- `uv sync` is defined in `Makefile` and backed by `pyproject.toml`/`uv.lock`.
- `.env` is required by `src/app/core/config.py`.
- Local app defaults and Alembic both expect a Postgres database reachable at `localhost:5432`.
- `pyproject.toml` defines the `serve` script used by `uv run serve`.

Equivalent wrappers:

- `make run` -> `uv run serve`
- `make migrate` -> `uv run alembic upgrade head`
- `make sync` -> `uv sync`

### Validation commands

These are the current executable validation commands the README should derive from:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```

Equivalent wrappers:

- `make lint`
- `make fmt`
- `make typecheck`
- `make test`

Test-only note:

- `tests/conftest.py` swaps the app DB dependency for a temporary SQLite database.
- Postgres, Docker, and `.env` are not prerequisites for `uv run pytest`.

### Alternative paths

- DB-only helper path: `docker compose up -d postgres` supports the primary host-based workflow by providing the expected local Postgres instance.
- Full container path: `docker compose up --build` is documented in `README.md`, and `docker-compose.yml` plus `Dockerfile` define it, but it should not be treated as the primary README path until the DB host mismatch below is resolved.

There are no service-specific alternatives beyond these because this repo contains a single service.

## Conflicts and Ambiguity

1. `README.md` says `uv run mypy src tests`, but the executable wrapper in `Makefile` runs `uv run mypy src`. The later README PR should choose one canonical typecheck command instead of copying both.
2. `README.md` advertises `docker compose up --build` as a full-stack path, but `docker-compose.yml` passes `.env` into the app container unchanged and `.env.example` sets `DATABASE_URL=...@localhost...`. From inside the app container, `localhost` points to the container itself, not the `postgres` service.
3. The readiness response is application-startup-only. `src/app/api/v1/endpoints/health.py` and `src/app/core/lifespan.py` do not check database connectivity, so the README should avoid implying that `/api/v1/health/ready` verifies Postgres availability.

## Recommendation for the README PR

Use the host-based `uv` workflow plus `docker compose up -d postgres` as the primary developer path. Keep Docker Compose as an alternative path for follow-up, but mark full containerized app startup as non-canonical until the env/database-host mismatch is fixed. Derive setup, run, and validation commands from the artifacts above rather than copying the current `README.md` prose.
