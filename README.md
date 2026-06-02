# FastAPI Service

This repository contains a single Python/FastAPI backend service. Today it includes versioned `/api/v1` health and user-management endpoints, SQLAlchemy-backed persistence, Alembic migrations, and automated tests.

## Who This Repo Is For

This README is for engineers who need to quickly confirm whether they are in the right codebase and where to start reading before contributing to the service.

## What This Repository Contains

- `src/app` holds the application package, service entrypoint, shared configuration, and request lifecycle code.
- `src/app/api/v1` contains the versioned API routers and endpoint handlers for health probes and users CRUD operations.
- `src/app/database` and `src/app/users` contain database session wiring, models, schemas, repository code, and user-domain services.
- `alembic` contains the database migration history for the service.
- `tests` covers the API surface and user service behavior.
- Top-level files such as `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, and `Makefile` define packaging and local workflow support for this service.

## Repository Orientation

This is a single-service repository, not a multi-app monorepo. Most contributors should start in `src/app`, then use `tests` to understand expected behavior and `alembic` when a change touches the database schema.
